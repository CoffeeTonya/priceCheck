import streamlit as st
import pandas as pd
import requests
import os
import csv

REQUEST_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
APP_ID = 1027604414937000350

st.title('楽天市場 商品価格検索')

# 機能選択
selected_item = st.sidebar.radio('使用機能を選んでください', ['個別検索', 'csv検索'])
st.sidebar.markdown("* * * ")


if selected_item == '個別検索':
    st.subheader('検索フォームに入力した商品を価格が安い順で出力')
    st.text('送料は商品個別で設定されている場合のみ（3,980円以上で送料無料の場合は送料別で取得される）')

    # 検索ワード
    search_keyword = st.sidebar.text_input('検索ワード')
    orFlag = st.sidebar.radio(
        "複数ワード入力時（0:AND検索 / 1:OR検索）",
        (0, 1)
    )
    st.sidebar.text('※スペースで複数ワード検索可')
    ng_keyword = st.sidebar.text_input('除外ワード', value="部品")
    hits = st.sidebar.number_input('検索数（30まで）', min_value=1, max_value=30, value=10, step=1)
    minPrice = st.sidebar.number_input('最小金額', value=1)
    maxPrice = st.sidebar.number_input('最大金額', value=999999)
    review = st.sidebar.radio(
        "レビュー（0:すべて / 1:レビューあり）",
        (0, 1)
    )

    tax01 = st.sidebar.checkbox('軽減税率')

    if search_keyword == '':
        st.text('検索ワードにテキストを入力してください')
    else:
        # 入力パラメータ
        search_params = {
            "format": "json",
            "keyword": search_keyword,
            "NGKeyword": ng_keyword,
            "orFlag": orFlag,
            "minPrice": minPrice,
            "maxPrice": maxPrice,
            "hasReviewFlag": review,
            "applicationId": [APP_ID],
            "availability": 1,
            "hits": hits,
            "page": 1,
            'sort': '+itemPrice',
        }

        # リクエスト
        response = requests.get(REQUEST_URL, search_params)
        result = response.json()

        # 格納
        item_list = []
        item_key = ['shopName', 'itemCode', 'itemName', 'itemPrice', 'pointRate', 'postageFlag', 'itemUrl', 'reviewCount', 'reviewAverage', 'endTime', 'mediumImageUrls']
        for i in range(0, len(result['Items'])):
            tmp_item = {}
            item = result['Items'][i]['Item']
            for key in item_key:
                if key in item:
                    tmp_item[key] = item[key]
            item_list.append(tmp_item.copy())

        df = pd.DataFrame(item_list)

        # カラムの順番と名前を変更
        df = df.reindex(columns=['mediumImageUrls', 'shopName', 'itemName', 'itemUrl', 'itemPrice', 'pointRate', 'postageFlag', 'reviewCount', 'reviewAverage', 'endTime'])
        df.columns = ['画像', 'ショップ', '商品名', 'URL', '商品価格', 'P倍付', '送料', 'レビュー件数', 'レビュー平均点', 'SALE終了']

        # 画像にリンクをつける
        df['画像'] = df.apply(
            lambda row: f'<a href="{row["URL"]}" target="_blank"><img src="{row["画像"][0]["imageUrl"]}"></a>' 
            if isinstance(row["画像"], list) and len(row["画像"]) > 0 and isinstance(row["画像"][0], dict) and "imageUrl" in row["画像"][0] 
            else '',
            axis=1
        )

        # ポイント計算
        if tax01:
            df['ポイント数'] = (round((df['商品価格'] / 1.08) * 0.01 * df['P倍付'])).astype(int)
        else:
            df['ポイント数'] = (round((df['商品価格'] / 1.1) * 0.01 * df['P倍付'])).astype(int)

        df['価格-ポイント'] = df['商品価格'] - df['ポイント数']

        df = df[['画像', 'ショップ', '商品名', '商品価格', '送料', 'ポイント数', '価格-ポイント', 'レビュー件数', 'レビュー平均点', 'SALE終了']]

        # 特定の条件に基づいて行に色を付ける関数
        def highlight_shop(row):
            return ['background-color: #ffe0ef;' if row['ショップ'] == 'FRESH ROASTER珈琲問屋 楽天市場店' else '' for _ in row]

        # スタイルを適用し、レビュー平均点を小数点第2位までフォーマット
        styled_df = df.style.apply(highlight_shop, axis=1).format({
            'レビュー平均点': "{:.2f}"
        })
        
        # インデックスをリセット
        df = df.reset_index(drop=True)

        # カスタムCSSを定義
        st.markdown("""
            <style>
            /* 正しいクラスセレクタの記述 */
                    
            .st-emotion-cache-13ln4jf {
                max-width: none;
                margin: 20px;
                font-size: 14px;
            }
            .st-emotion-cache-1rsyhoq th {
                text-align: left;
            }
            </style>
            """, unsafe_allow_html=True)

        st.text('商品価格昇順 / 画像クリックで商品ページへ')
        
        # CSVファイルとしてデータを出力するボタン
        csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

        st.download_button(
            label="CSVファイルとしてダウンロード",
            data=csv,
            file_name='楽天市場検索結果.csv',
            mime='text/csv',
        )
        
        # Streamlitアプリ内でテーブルを表示
        st.write(styled_df.to_html(escape=False, index=False), unsafe_allow_html=True)



# ------------------------------------------------------------------------------------

else:
    st.subheader('csvファイル内にある各商品の最安値を出力')
    st.text('送料は商品個別で設定されている場合のみ（3,980円以上で送料無料の場合は送料別で取得される）')
    # ファイルのアップロードウィジェット
    uploaded_file = st.sidebar.file_uploader("CSVファイルをアップロード", type="csv")
    st.sidebar.text("検索ワード,除外ワード")

    tax01 = st.sidebar.checkbox('軽減税率')

    # ファイルがアップロードされたか確認
    if uploaded_file is not None:
        try:
            # アップロードされたファイルをShift_JISで読み込み
            df = pd.read_csv(uploaded_file, encoding='utf-8')

            # 結果を格納するリスト
            item_list = []

            # CSVの各行を処理する
            for index, row in df.iterrows():
                search_keyword = row[13]
                # ng_keyword = '部品'

                # 入力パラメータ
                search_params = {
                    "format": "json",
                    "keyword": search_keyword,
                    # "NGKeyword": ng_keyword,
                    "applicationId": APP_ID,
                    "availability": 0,
                    "hits": 1,
                    "page": 1,
                    'sort': '+itemPrice',
                }

                # リクエストを送信
                response = requests.get(REQUEST_URL, search_params)
                result = response.json()

                # 格納
                item_key = ['shopName', 'itemCode', 'itemName', 'itemPrice', 'pointRate', 'postageFlag', 'itemUrl', 'reviewCount', 'reviewAverage', 'endTime', 'mediumImageUrls']
                for i in range(len(result['Items'])):
                    tmp_item = {}
                    item = result['Items'][i]['Item']
                    for key in item_key:
                        if key in item:
                            tmp_item[key] = item[key]
                    item_list.append(tmp_item.copy())

            # 結果をDataFrameに変換
            df_result = pd.DataFrame(item_list)

            # カラムの順番と名前を変更
            df_result = df_result.reindex(columns=['mediumImageUrls', 'shopName', 'itemName', 'itemUrl', 'itemPrice', 'pointRate', 'postageFlag', 'reviewCount', 'reviewAverage', 'endTime'])
            df_result.columns = ['画像', 'ショップ', '商品名', 'URL', '商品価格', 'P倍付', '送料', 'レビュー件数', 'レビュー平均点', 'SALE終了']

            # 画像にリンクをつける
            df_result['画像'] = df_result.apply(
                lambda row: f'<a href="{row["URL"]}" target="_blank"><img src="{row["画像"][0]["imageUrl"]}"></a>' 
                if isinstance(row["画像"], list) and len(row["画像"]) > 0 and isinstance(row["画像"][0], dict) and "imageUrl" in row["画像"][0] 
                else '',
                axis=1
            )

            # ポイント計算
            if tax01:
                df_result['ポイント数'] = (round((df_result['商品価格'] / 1.08) * 0.01 * df_result['P倍付'])).astype(int)
            else:
                df_result['ポイント数'] = (round((df_result['商品価格'] / 1.1) * 0.01 * df_result['P倍付'])).astype(int)

            df_result['価格-ポイント'] = df_result['商品価格'] - df_result['ポイント数']

            df_result = df_result[['画像', 'ショップ', '商品名', '商品価格', '送料', 'ポイント数', '価格-ポイント', 'レビュー件数', 'レビュー平均点', 'SALE終了']]


            # 特定の条件に基づいて行に色を付ける関数
            def highlight_shop(row):
                return ['background-color: #ffe0ef;' if row['ショップ'] == 'FRESH ROASTER珈琲問屋 楽天市場店' else '' for _ in row]

            # スタイルを適用し、レビュー平均点を小数点第2位までフォーマット
            styled_df = df_result.style.apply(highlight_shop, axis=1).format({
                'レビュー平均点': "{:.2f}"
            })
            
            # インデックスをリセット
            df = df.reset_index(drop=True)

            # カスタムCSSを定義
            st.markdown("""
                <style>
                /* 正しいクラスセレクタの記述 */
                .st-emotion-cache-13ln4jf {
                    max-width: none;
                    margin: 20px;
                    font-size: 14px;
                }
                .st-emotion-cache-1rsyhoq th {
                    text-align: left;
                }
                </style>
                """, unsafe_allow_html=True)

            # CSVファイルとしてデータを出力するボタン
            csv = df_result.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

            st.download_button(
                label="CSVファイルとしてダウンロード",
                data=csv,
                file_name='楽天市場検索結果.csv',
                mime='text/csv',
            )

            # Streamlitで結果を表示
            st.write(styled_df.to_html(escape=False, index=False), unsafe_allow_html=True)


        except Exception as e:
            # エラーメッセージを表示
            st.error(f"データの読み込み中にエラーが発生しました: {e}")
    else:
        # ファイルがアップロードされていない場合のメッセージ
        st.write("ファイルをアップロードしてください")
