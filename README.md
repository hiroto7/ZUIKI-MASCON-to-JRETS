# ZUIKI-MASCON-to-JRETS

JR東日本トレインシミュレータ (JRETS) をズイキマスコンで操作できるようにするための非公式MODです。

JRETSは2024年5月からズイキマスコンを公式にサポートするようになりましたが、その後サービス開始されたGeForce NOW版では非対応となっています。この非公式MODでは、ズイキマスコンからの入力をキーボード入力にマッピングすることで、擬似的にGeForce NOW版でもズイキマスコンで操作できるようにします。

## 動作環境

macOS上のGeForce NOWで動作するように開発しています。

- Mac mini (2024)
- macOS Sequoia 15.3
- Python 3.13.1
- ズイキマスコン ZKNS-013
- JR東日本トレインシミュレータ Ver. 1.0.1.561
- GeForce NOW

## 使い方

1. リポジトリをクローンする
   ```
   git clone https://github.com/hiroto7/ZUIKI-MASCON-to-JRETS.git
   ```
2. パッケージをインストールする
   ```
   cd ZUIKI-MASCON-to-JRETS
   pip3 install -r requirements.txt
   ```
3. main.py を実行する
   ```
   python3 main.py
   ```
4. この状態でシミュレータをプレイする
5. <kbd>control</kbd> + <kbd>C</kbd> で終了

## ボタンのマッピング

デフォルトのマッピングは、通常版（ダウンロード版）でズイキマスコンを使用したときと同じ挙動となるよう設定されています。なおHOMEボタンとキャプチャーボタンは、GeForce Nowアプリのキーボードショートカットにマッピングされています。

このマッピングは main.py 内の `MAPPING_TO_KEYBOARD` を編集することでカスタマイズできます。ただしZLボタンにはマッピングを設定できません。

## 制約

1ハンドルマスコン以外には対応していません。
