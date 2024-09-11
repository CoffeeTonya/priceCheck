import streamlit as st
import pandas as pd
import requests
import os
import csv

REQUEST_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706"
APP_ID = 1027604414937000350

st.title('楽天市場 商品価格検索')
st.text('検索ワードを入力してください（除外ワードは必要に応じ修正）')



# ------------------------------------------------------------------------------------

# ファイルのアップロードウィジェット
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type="csv")

# ファイルがアップロードされたか確認
if uploaded_file is not None:
    try:
        # アップロードされたファイルを読み込み
        df = pd.read_csv(uploaded_file, encoding='shift_jis')

        item_list = [] 
        for i in df:
            serch_keyword = df[0][i]
            ng_keyword = df[1][i]

            # 入力パラメータ
            serch_params={
                "format" : "json",
                "keyword" : serch_keyword,
                "NGKeyword":ng_keyword,
                "applicationId" : [APP_ID],
                "availability" : 0,
                "hits" : 1,
                "page" : 1,
                'sort': '+itemPrice',
            }

            # リクエスト
            response = requests.get(REQUEST_URL, serch_params)
            result = response.json()

            # 格納
            item_key = ['shopName', 'itemCode', 'itemName', 'itemPrice', 'pointRate', 'postageFlag', 'itemUrl', 'reviewCount', 'reviewAverage', 'endTime']
            for i in range(0, len(result['Items'])):
                tmp_item = {}
                item = result['Items'][i]['Item']
                for key, value in item.items():
                    if key in item_key:
                        tmp_item[key] = value
                item_list.append(tmp_item.copy())

        df_ = pd.DataFrame(item_list)

        # カラムの順番と名前を変更
        df_ = df_.reindex(columns=['mediumImageUrls', 'shopName', 'itemName', 'itemUrl', 'itemPrice', 'pointRate', 'postageFlag', 'reviewCount', 'reviewAverage', 'endTime'])
        df_.columns = ['画像', 'ショップ', '商品名', 'URL', '商品価格', 'P倍付', '送料', 'レビュー件数', 'レビュー平均点', 'SALE終了']

        # 画像にリンクをつける
        df_['画像'] = df_.apply(
            lambda row: f'<a href="{row["URL"]}" target="_blank"><img src="{row["画像"][0]["imageUrl"]}"></a>' 
            if isinstance(row["画像"], list) and len(row["画像"]) > 0 and isinstance(row["画像"][0], dict) and "imageUrl" in row["画像"][0] 
            else '',
            axis=1
        )

        # ポイント計算
        if tax01:
            df_['ポイント数'] = (round((df_['商品価格'] / 1.08) * 0.01 * df_['P倍付'])).astype(int)
        else:
            df_['ポイント数'] = (round((df_['商品価格'] / 1.1) * 0.01 * df_['P倍付'])).astype(int)

        df_['価格-ポイント'] = df_['商品価格'] - df_['ポイント数']

        df_ = df_[['画像', 'ショップ', '商品名', '商品価格', 'P倍付', 'ポイント数', '価格-ポイント', '送料', 'レビュー件数', 'レビュー平均点', 'SALE終了']]

        # 特定の条件に基づいて行に色を付ける関数
        def highlight_shop(row):
            return ['background-color: #e5f2ff;' if row['ショップ'] == 'FRESH ROASTER珈琲問屋 楽天市場店' else '' for _ in row]

        # インデックスをリセット
        df_ = df_.reset_index(drop=True)
        
        # データを表示
        st.write(df_)

    except Exception as e:
        # エラーメッセージを表示
        st.error(f"データの読み込み中にエラーが発生しました: {e}")
else:
    # ファイルがアップロードされていない場合のメッセージ
    st.write("ファイルをアップロードしてください")
