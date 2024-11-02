import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
import csv
from datetime import datetime

REQUEST_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
APP_ID = 1027604414937000350

st.title('楽天市場 商品価格検索')

# 機能選択
selected_item = st.sidebar.radio('検索機能を選んでください', ['個別検索', 'csv検索', '価格更新ファイル作成'])
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
    ng_keyword = st.sidebar.text_input('除外ワード', value="部品 中古")
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
            lambda row: f'<a href="{row["URL"]}" target="_blank"><img src="{row["画像"][0]["imageUrl"]}" width="100"></a>' 
            if isinstance(row["画像"], list) and len(row["画像"]) > 0 and isinstance(row["画像"][0], dict) and "imageUrl" in row["画像"][0] 
            else '',
            axis=1
        )

        # 商品名にリンクをつける
        df['商品名'] = df.apply(
            lambda row: f'<a href="{row["URL"]}" target="_blank">{row["商品名"]}</a>',
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

if selected_item == 'csv検索':
    st.subheader('csvファイル内にある各商品の最安値を出力')
    st.text('送料は商品個別で設定されている場合のみ（3,980円以上で送料無料の場合は送料別で取得される）')
    st.sidebar.markdown('csv1: リスト内商品すべて検索<br>csv1&2: 販売中のみ検索<br>csv2: 検索不可', unsafe_allow_html=True)
    st.sidebar.markdown("* * * ")

    uploaded_file1 = st.sidebar.file_uploader("【csv1】汎用明細T9999：商品マスタ", type="csv", key="csv1")
    uploaded_file2 = st.sidebar.file_uploader("【csv2】goods：商品エクスポート", type="csv", key="csv2")
    st.sidebar.markdown("* * * ")
    ng_keyword = st.sidebar.text_input('除外ワード', value="部品 中古")

    # ファイルがアップロードされたか確認
    if uploaded_file1 is not None:
        if uploaded_file2 is None:
            try:
                # アップロードされたファイルをShift_JISで読み込み
                df = pd.read_csv(uploaded_file1, encoding='utf-8')

                # 結果を格納するリスト
                item_list = []

                # CSVの各行を処理する
                for index, row in df.iterrows():
                    search_keyword = row['JANコード']
                    minPrice = int(row['仕入単価'])
                    maxPrice = int(row['通販単価'])
                    product_code = row['商品コード']
                    purchase_cost = int(row['仕入単価']) 
                    web_price = int(row['通販単価']) 
                    tax_class = row['税率区分名'] 
                    ships_free = row['商品分類6名'] 
                    
                    # 入力パラメータ
                    search_params = {
                        "format": "json",
                        "keyword": search_keyword,
                        "NGKeyword": ng_keyword,
                        "minPrice": minPrice,
                        "maxPrice": maxPrice,
                        "applicationId": APP_ID,
                        "availability": 1,
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
                        tmp_item['商品コード'] = product_code
                        tmp_item['仕入単価'] = purchase_cost
                        tmp_item['通販単価'] = web_price
                        tmp_item['税率区分名'] = tax_class
                        tmp_item['商品分類6名'] = ships_free
                        item_list.append(tmp_item.copy())

                # 結果をDataFrameに変換
                df_result = pd.DataFrame(item_list)


                # カラムの順番と名前を変更
                df_result = df_result.reindex(columns=['商品コード', 'mediumImageUrls', 'shopName', 'itemName', 'itemUrl', 'itemPrice', 'pointRate', 'postageFlag', 'endTime', '仕入単価', '通販単価', '税率区分名', '商品分類6名'])
                df_result.columns = ['商品コード', '画像', 'ショップ', '商品名', 'URL', '商品価格', 'P倍付', '送料', 'SALE終了', '仕入単価', '通販単価', '税率区分名', '送料区分']

                # 画像にリンクをつける
                df_result['画像'] = df_result.apply(
                    lambda row: f'<a href="{row["URL"]}" target="_blank"><img src="{row["画像"][0]["imageUrl"]}" width="100"></a>' 
                    if isinstance(row["画像"], list) and len(row["画像"]) > 0 and isinstance(row["画像"][0], dict) and "imageUrl" in row["画像"][0] 
                    else '',
                    axis=1
                )

                # 商品名にリンクをつける
                df_result['商品名'] = df_result.apply(
                    lambda row: f'<a href="{row["URL"]}" target="_blank">{row["商品名"]}</a>',
                    axis=1
                )

                # ポイント計算（税率区分名に基づいて計算）
                df_result['ポイント数'] = df_result.apply(
                    lambda row: round((row['商品価格'] / 1.08) * 0.01 * row['P倍付']) if row['税率区分名'] == '軽減税率' else round((row['商品価格'] / 1.1) * 0.01 * row['P倍付']),
                    axis=1
                )
                df_result['価格-ポイント'] = df_result['商品価格'] - df_result['ポイント数']

                # ポイント計算（税率区分名に基づいて計算）
                df_result['最安時粗利額'] = df_result.apply(
                    lambda row: (row['商品価格'] - round(row['仕入単価']*1.08)) if row['税率区分名'] == '軽減税率' else (row['商品価格'] - round(row['仕入単価']*1.1)),
                    axis=1
                )
                df_result['最安時粗利率'] = df_result.apply(
                    lambda row: int((1 - (row['仕入単価'] * 1.08) / row['商品価格'])) if row['税率区分名'] == '軽減税率' else int((1 - (row['仕入単価'] * 1.1) / row['商品価格'])),
                    axis=1
                )
                df_result['価格-ポイント'] = df_result['商品価格'] - df_result['ポイント数']
                df_result['価格差'] = df_result['通販単価'] - df_result['商品価格']
                df_result['変更価格'] = ''
                df_result['変更後粗利額'] = df.apply(
                    lambda row: f"=IF(L{row.name + 2}=\"課税\", F{row.name + 2} - H{row.name + 2}*1.1, F{row.name + 2} - H{row.name + 2}*1.08)",
                    axis=1
                )
                df_result['変更後粗利率'] = df.apply(
                    lambda row: f"=ROUNDDOWN(IF(L{row.name + 2}=\"課税\", (1-(H{row.name + 2})*1.1/F{row.name + 2}), (1-(H{row.name + 2})*1.08/F{row.name + 2})),2)",
                    axis=1
                )

                df_result = df_result[['商品コード', '画像', 'ショップ', '商品名', '商品価格', '変更価格', '送料', '仕入単価', '通販単価', '価格差', '送料区分', '税率区分名', '最安時粗利額', '最安時粗利率', '変更後粗利額', '変更後粗利率']]


                # 特定の条件に基づいて行に色を付ける関数
                def highlight_shop(row):
                    return ['background-color: #ffe0ef;' if row['ショップ'] == 'FRESH ROASTER珈琲問屋 楽天市場店' else '' for _ in row]

                # スタイルを適用し、レビュー平均点を小数点第2位までフォーマット
                styled_df = df_result.style.apply(highlight_shop, axis=1).format({
                    'レビュー平均点': "{:.2f}"
                })

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
                st.error(f"csv1の読み込み中にエラーが発生しました: {e}")
        
        else:
            try:
                df1 = pd.read_csv(uploaded_file1, encoding='utf-8')
                df2 = pd.read_csv(uploaded_file2, encoding='cp932')
                df_merged = pd.merge(df1, df2, on='商品コード', how='inner')
                df_merged = df_merged[['商品コード', '商品名', 'JANコード', '通販単価', '仕入単価', '税率区分名', '商品分類6名']]

                # 結果を格納するリスト
                item_list = []

                # CSVの各行を処理する
                for index, row in df_merged.iterrows():
                    search_keyword = row['JANコード']
                    minPrice = int(row['仕入単価'])
                    maxPrice = int(row['通販単価'])
                    product_code = row['商品コード']
                    purchase_cost = int(row['仕入単価']) 
                    web_price = int(row['通販単価']) 
                    tax_class = row['税率区分名'] 
                    ships_free = row['商品分類6名'] 

                    # 入力パラメータ
                    search_params = {
                        "format": "json",
                        "keyword": search_keyword,
                        "NGKeyword": ng_keyword,
                        "minPrice": minPrice,
                        "maxPrice": maxPrice,
                        "applicationId": APP_ID,
                        "availability": 1,
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
                        tmp_item['商品コード'] = product_code
                        tmp_item['仕入単価'] = purchase_cost
                        tmp_item['通販単価'] = web_price
                        tmp_item['税率区分名'] = tax_class
                        tmp_item['商品分類6名'] = ships_free
                        item_list.append(tmp_item.copy())

                # 結果をDataFrameに変換
                df_result = pd.DataFrame(item_list)

                # カラムの順番と名前を変更
                df_result = df_result.reindex(columns=['商品コード', 'mediumImageUrls', 'shopName', 'itemName', 'itemUrl', 'itemPrice', 'pointRate', 'postageFlag', 'endTime', '仕入単価', '通販単価', '税率区分名', '商品分類6名'])
                df_result.columns = ['商品コード', '画像', 'ショップ', '商品名', 'URL', '商品価格', 'P倍付', '送料', 'SALE終了', '仕入単価', '通販単価', '税率区分名', '送料区分']

                # 画像にリンクをつける
                df_result['画像'] = df_result.apply(
                    lambda row: f'<a href="{row["URL"]}" target="_blank"><img src="{row["画像"][0]["imageUrl"]}" width="100"></a>' 
                    if isinstance(row["画像"], list) and len(row["画像"]) > 0 and isinstance(row["画像"][0], dict) and "imageUrl" in row["画像"][0] 
                    else '',
                    axis=1
                )

                # 商品名にリンクをつける
                df_result['商品名'] = df_result.apply(
                    lambda row: f'<a href="{row["URL"]}" target="_blank">{row["商品名"]}</a>',
                    axis=1
                )

                # ポイント計算（税率区分名に基づいて計算）
                df_result['ポイント数'] = df_result.apply(
                    lambda row: round((row['商品価格'] / 1.08) * 0.01 * row['P倍付']) if row['税率区分名'] == '軽減税率' else round((row['商品価格'] / 1.1) * 0.01 * row['P倍付']),
                    axis=1
                )
                df_result['価格-ポイント'] = df_result['商品価格'] - df_result['ポイント数']

                # ポイント計算（税率区分名に基づいて計算）
                df_result['最安時粗利額'] = df_result.apply(
                    lambda row: (row['商品価格'] - round(row['仕入単価']*1.08)) if row['税率区分名'] == '軽減税率' else (row['商品価格'] - round(row['仕入単価']*1.1)),
                    axis=1
                )
                df_result['最安時粗利率'] = df_result.apply(
                    lambda row: int((1 - (row['仕入単価'] * 1.08) / row['商品価格'])) if row['税率区分名'] == '軽減税率' else int((1 - (row['仕入単価'] * 1.1) / row['商品価格'])),
                    axis=1
                )
                df_result['価格-ポイント'] = df_result['商品価格'] - df_result['ポイント数']
                df_result['価格差'] = df_result['通販単価'] - df_result['商品価格']
                df_result['変更価格'] = ''
                df_result['変更後粗利額'] = df.apply(
                    lambda row: f"=IF(L{row.name + 2}=\"課税\", F{row.name + 2} - H{row.name + 2}*1.1, F{row.name + 2} - H{row.name + 2}*1.08)",
                    axis=1
                )
                df_result['変更後粗利率'] = df.apply(
                    lambda row: f"=ROUNDDOWN(IF(L{row.name + 2}=\"課税\", (1-(H{row.name + 2})*1.1/F{row.name + 2}), (1-(H{row.name + 2})*1.08/F{row.name + 2})),2)",
                    axis=1
                )

                df_result = df_result[['商品コード', '画像', 'ショップ', '商品名', '商品価格', '変更価格', '送料', '仕入単価', '通販単価', '価格差', '送料区分', '税率区分名', '最安時粗利額', '最安時粗利率', '変更後粗利額', '変更後粗利率']]

                # 特定の条件に基づいて行に色を付ける関数
                def highlight_shop(row):
                    return ['background-color: #ffe0ef;' if row['ショップ'] == 'FRESH ROASTER珈琲問屋 楽天市場店' else '' for _ in row]
                
                # スタイルを適用し、レビュー平均点を小数点第2位までフォーマット
                styled_df = df_result.style.apply(highlight_shop, axis=1).format({
                    'レビュー平均点': "{:.2f}"
                })

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
                st.error(f"csv1の読み込み中にエラーが発生しました: {e}")

# ------------------------------------------------------------------------------------

if selected_item == '価格更新ファイル作成':
    st.subheader('価格更新用のcsvファイルを作成')

    uploaded_file3 = st.sidebar.file_uploader("csv検索でダウンロードしたファイル", type="csv", key="csv3")

    # ファイルがアップロードされたか確認
    if uploaded_file3 is not None:
        try:
            df00 = pd.read_csv(uploaded_file3, encoding='utf-8')

            # 楽天用データの作成
            df01 = df00[['商品コード', '商品価格', '通販単価']]
            df01 = df01.rename(columns={'商品コード': '商品管理番号（商品URL）', '商品価格': '販売価格'})

            # 商品番号関連の列を文字列型に変換
            df01['商品番号'] = df01['商品管理番号（商品URL）'].astype(str)
            df01['SKU管理番号'] = df01['商品管理番号（商品URL）'].astype(str)
            df01['システム連携用SKU番号'] = df01['商品管理番号（商品URL）'].astype(str)

            # 販売価格をstr型に変換（int型だとNaNを入れられないため）
            df01['販売価格'] = df01['販売価格'].astype(str)
            df01['表示価格'] = df01['通販単価'].astype(str)

            # 新しい列を追加して、値を入れない（NaNに設定）
            df01['バリエーション項目キー1'] = np.nan
            df01['バリエーション項目キー2'] = np.nan
            df01['バリエーション項目選択肢1'] = np.nan
            df01['バリエーション項目選択肢2'] = np.nan
            df01['二重価格文言管理番号'] = str(1)

            # 行を複製し、元の行の販売価格、SKU関連の値を削除（NaNに変更）
            for i in range(0, len(df01)):
                # 複製する行をコピー
                duplicated_row = df01.loc[i].copy()

                # 元のデータの「販売価格」とSKU関連番号をNaNにする
                df01.loc[i, '販売価格'] = np.nan
                df01.loc[i, '表示価格'] = np.nan
                df01.loc[i, 'SKU管理番号'] = np.nan
                df01.loc[i, 'システム連携用SKU番号'] = np.nan
                df01.loc[i, '二重価格文言管理番号'] = np.nan

                # 複製した行をデータフレームに追加（複製行は元の値を保持）
                df01 = pd.concat([df01, pd.DataFrame([duplicated_row])], ignore_index=True)

            # 商品管理番号（商品URL）で並び替え
            df01_sorted = df01.sort_values(by=['商品管理番号（商品URL）', '商品番号'])

            # 販売価格に値が入っている場合、商品番号をNaNにする
            df01_sorted.loc[df01_sorted['販売価格'].notna(), '商品番号'] = np.nan
            df_rakuten = df01_sorted[['商品管理番号（商品URL）', '商品番号', 'SKU管理番号', 'システム連携用SKU番号', 'バリエーション項目キー1', 'バリエーション項目キー2', 'バリエーション項目選択肢1', 'バリエーション項目選択肢2', '販売価格', '表示価格', '二重価格文言管理番号']]

            # CSVファイルとしてデータを出力するボタン
            csv_rakuten = df_rakuten.to_csv(index=False, encoding='shift-jis').encode('utf-8-sig')

            st.download_button(
                label="楽天用CSVファイルをダウンロード",
                data=csv_rakuten,
                file_name='楽天アップロード用.csv',
                mime='text/csv',
            )

            # Yahoo用データの作成
            df02 = df00[['商品コード', '通販単価', '商品価格']]
            df02 = df02.rename(columns={'商品コード': 'code', '通販単価': 'original-price', '商品価格': 'price'})

            # 販売価格をstr型に変換（int型だとNaNを入れられないため）
            df02['original-price'] = df02['original-price'].astype(str)
            df02['price'] = df02['price'].astype(str)

            # CSVファイルとしてデータを出力するボタン
            csv_yahoo = df02.to_csv(index=False, encoding='shift-jis').encode('utf-8-sig')

            st.download_button(
                label="Yahoo用CSVファイルをダウンロード",
                data=csv_yahoo,
                file_name='Yahooアップロード用.csv',
                mime='text/csv',
            )

            # 自社サイト用データの作成
            # 現在の日付と時刻を取得
            now = datetime.now()

            # 月や日、時間をゼロパディングなしにする
            start_date = f"{now.year}/{now.month}/{now.day} 00:00"
            end_date = f"2050/12/31 23:59"

            # 商品コードはint型、商品価格はfloat型に変換
            df03 = df00[['商品コード', '通販単価', '商品価格', '税率区分名']]
            df03 = df03.rename(columns={'商品コード': '品番3', '通販単価': '販売価格(税込)[レベル1：通常会員]', '商品価格': 'セール価格(税込)[レベル1：通常会員]'})

            # 通常会員の設定
            df03['販売価格(税込)[レベル1：通常会員]'] = df03['販売価格(税込)[レベル1：通常会員]']
            df03['ポイント数[レベル1：通常会員]'] = df03.apply(
                lambda row: int(row['販売価格(税込)[レベル1：通常会員]'] / 1.1 * 0.01) if row['税率区分名'] == '課税' else int(row['販売価格(税込)[レベル1：通常会員]'] / 1.08 * 0.01),
                axis=1
            )
            df03['セール開始日[レベル1：通常会員]'] = start_date
            df03['セール終了日[レベル1：通常会員]'] = end_date
            df03['セール価格(税込)[レベル1：通常会員]'] = df03['セール価格(税込)[レベル1：通常会員]']
            df03['セールポイント数[レベル1：通常会員]'] = df03.apply(
                lambda row: int(row['セール価格(税込)[レベル1：通常会員]'] / 1.1 * 0.01) if row['税率区分名'] == '課税' else int(row['セール価格(税込)[レベル1：通常会員]'] / 1.08 * 0.01),
                axis=1
            )

            # シルバー会員の設定
            df03['販売価格(税込)[レベル1：シルバー会員]'] = df03['販売価格(税込)[レベル1：通常会員]']
            df03['ポイント数[レベル1：シルバー会員]'] = df03.apply(
                lambda row: int(row['販売価格(税込)[レベル1：シルバー会員]'] / 1.1 * 0.01) if row['税率区分名'] == '課税' else int(row['販売価格(税込)[レベル1：シルバー会員]'] / 1.08 * 0.01),
                axis=1
            )
            df03['セール開始日[レベル1：シルバー会員]'] = start_date
            df03['セール終了日[レベル1：シルバー会員]'] = end_date
            df03['セール価格(税込)[レベル1：シルバー会員]'] = df03['セール価格(税込)[レベル1：通常会員]']
            df03['セールポイント数[レベル1：シルバー会員]'] = df03.apply(
                lambda row: int(row['セール価格(税込)[レベル1：シルバー会員]'] / 1.1 * 0.01) if row['税率区分名'] == '課税' else int(row['セール価格(税込)[レベル1：シルバー会員]'] / 1.08 * 0.01),
                axis=1
            )

            # ゴールド会員の設定
            df03['販売価格(税込)[レベル1：ゴールド会員]'] = df03['販売価格(税込)[レベル1：通常会員]']
            df03['ポイント数[レベル1：ゴールド会員]'] = df03.apply(
                lambda row: int(row['販売価格(税込)[レベル1：ゴールド会員]'] / 1.1 * 0.02) if row['税率区分名'] == '課税' else int(row['販売価格(税込)[レベル1：ゴールド会員]'] / 1.08 * 0.02),
                axis=1
            )
            df03['セール開始日[レベル1：ゴールド会員]'] = start_date
            df03['セール終了日[レベル1：ゴールド会員]'] = end_date
            df03['セール価格(税込)[レベル1：ゴールド会員]'] = df03['セール価格(税込)[レベル1：通常会員]']
            df03['セールポイント数[レベル1：ゴールド会員]'] = df03.apply(
                lambda row: int(row['セール価格(税込)[レベル1：ゴールド会員]'] / 1.1 * 0.02) if row['税率区分名'] == '課税' else int(row['セール価格(税込)[レベル1：ゴールド会員]'] / 1.08 * 0.02),
                axis=1
            )

            # プラチナ会員の設定
            df03['販売価格(税込)[レベル1：プラチナ会員]'] = df03['販売価格(税込)[レベル1：通常会員]']
            df03['ポイント数[レベル1：プラチナ会員]'] = df03.apply(
                lambda row: int(row['販売価格(税込)[レベル1：プラチナ会員]'] / 1.1 * 0.03) if row['税率区分名'] == '課税' else int(row['販売価格(税込)[レベル1：プラチナ会員]'] / 1.08 * 0.03),
                axis=1
            )
            df03['セール開始日[レベル1：プラチナ会員]'] = start_date
            df03['セール終了日[レベル1：プラチナ会員]'] = end_date
            df03['セール価格(税込)[レベル1：プラチナ会員]'] = df03['セール価格(税込)[レベル1：通常会員]']
            df03['セールポイント数[レベル1：プラチナ会員]'] = df03.apply(
                lambda row: int(row['セール価格(税込)[レベル1：プラチナ会員]'] / 1.1 * 0.03) if row['税率区分名'] == '課税' else int(row['セール価格(税込)[レベル1：プラチナ会員]'] / 1.08 * 0.03),
                axis=1
            )

            df_tonya = df03[['品番3'
                        ,'販売価格(税込)[レベル1：通常会員]', 'ポイント数[レベル1：通常会員]', 'セール開始日[レベル1：通常会員]', 'セール終了日[レベル1：通常会員]', 'セール価格(税込)[レベル1：通常会員]', 'セールポイント数[レベル1：通常会員]'
                        ,'販売価格(税込)[レベル1：シルバー会員]', 'ポイント数[レベル1：シルバー会員]', 'セール開始日[レベル1：シルバー会員]', 'セール終了日[レベル1：シルバー会員]', 'セール価格(税込)[レベル1：シルバー会員]', 'セールポイント数[レベル1：シルバー会員]'
                        ,'販売価格(税込)[レベル1：ゴールド会員]', 'ポイント数[レベル1：ゴールド会員]', 'セール開始日[レベル1：ゴールド会員]', 'セール終了日[レベル1：ゴールド会員]', 'セール価格(税込)[レベル1：ゴールド会員]', 'セールポイント数[レベル1：ゴールド会員]'
                        ,'販売価格(税込)[レベル1：プラチナ会員]', 'ポイント数[レベル1：プラチナ会員]', 'セール開始日[レベル1：プラチナ会員]', 'セール終了日[レベル1：プラチナ会員]', 'セール価格(税込)[レベル1：プラチナ会員]', 'セールポイント数[レベル1：プラチナ会員]'
                        ]]

            # CSVファイルとしてデータを出力するボタン
            csv_tonya = df_tonya.to_csv(index=False, encoding='shift-jis').encode('utf-8-sig')

            st.download_button(
                label="自社用CSVファイルをダウンロード",
                data=csv_tonya,
                file_name='自社アップロード用.csv',
                mime='text/csv',
            )

            # Streamlitで結果を表示（スタイリングが必要であれば適用）
            st.write('csvファイルを出力できます')

        except Exception as e:
            # エラーメッセージを表示
            st.error(f"csv1の読み込み中にエラーが発生しました: {e}")
