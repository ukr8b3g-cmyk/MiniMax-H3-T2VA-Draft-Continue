# Phase 3A — START BBOX連携 / v1.3.0

## 今回追加したもの

上流に置く任意ノード **H3 Structured Layout Audit (START)** を追加しました。既存の **H3 Draft Sampler / H3 Continue Sampler** のポートは変更していません。

H3 Structured Canvasの既存 `H3_LAYOUT`（`h3_structured_canvas/0.9`）と、Prompterが作った文字列を監査用metadataとしてCONDITIONINGへ添付します。Canvas側のリポジトリ変更・import依存・追加pip導入は不要です。Canvasを使用しないWorkflowは従来どおり使えます。

## 接続

```text
Canvas.layout ──→ Structured Prompter.layout
      │                    │ prompt
      │                    ├──→ MiniMax H3 conditioner.prompt
      │                    └──→ Layout Audit.compiled_prompt
      └───────────────────────→ Layout Audit.layout
H3 conditioner.positive ──────→ Layout Audit.positive
Layout Audit.positive → BasicGuider → Draft → Continue → 既存Decode/Save
H3 conditioner.LATENT ───────────────→ Draft
```

**同じPrompterの出力**をH3 conditionerとLayout Auditの両方へ接続します。Canvasのwidth/heightもconditionerへ接続してください。Layout AuditはテキストをEncodeせず、画像・Reference・conditioning tensor・latentも変更しません。

完成した接続例は `examples/H3-START-Layout-Draft.json` です。実機確認済みの共通4-step Turbo、Total 6、Preview 3、Euler/simpleを維持し、START A/Bの2人を指定しています。モデルファイル名は手持ちのものを選択してください。

## 保持・変更検出

監査対象は、STARTのslot、BBOX、Canvas寸法、Layout内のID/label/description等の意味情報と、改変しないプロンプト原文です。正規化した構図hashと、原文のUTF-8 SHA-256を記録します。

`100` と `100.0` は同じ数値として扱います。BBOX座標を丸めたり、範囲外をclampしたりしません。Canvasのグリッド、選択slot、枠色等のUI表示情報は構図hashから除外します。ただし、既存の厳格なWorkflow全体の変更検出は維持するため、UI値の変更でも再Previewが必要になる場合があります。

Preview後に構図・プロンプト・metadataが変わった場合、古いGOは停止します。新しいPreviewを確認してからGOしてください。Reference、モデル、LoRA、SIGMAS、Seed等の既存検証も残します。

## Reportの確認箇所

Draftは `state.structured_layout`、Continueは `structured_layout` を確認します。

- `present`: 構図metadataの有無
- `items`: provider、schema、scope、slots、ir_hash、prompt_hash
- `payload_sha256`: 監査情報のhash
- `semantic_accuracy_verified=false`: BBOXどおりの画質を自動認定しない
- `prompt_binding_verified=false`: 任意のCONDITIONINGがこの文字列から作られたことをmetadataだけで証明しない

**この追加はBBOXへの追従能力を高めるものではありません。** 上流で指定した構図を、同じ条件でPreview/Continueできるよう記録・保護する機能です。

## 対象と制約

Phase 3Aの監査ノードは、画面内0～1000のxyxy、STARTのみ、A/B/Cの1～3枠が対象です。END／Timeline／Multi-Key／offscreenデータを受け取った場合、黙って削除せず対象外として停止します。これらの機能を既存の一般Workflowから削除したわけではありません。必要なWorkflowでは監査ノードを追加せず従来の接続を維持してください。

Stateは同一バックエンドセッション内です。永続保存、Sampler追加、Preview画像へのBBOX重ね描きは今回の範囲外です。

## 検証範囲

新規CPUテスト36件で、metadataの正規化、入力保護、変更検出、状態復元、数値処理への非介入、Reference共存、Workflow配線を確認しました。モデルはHost代替であり、新機能の実H3 GPU推論・Canvas実画面・生成配置の精度は未確認です。

実機は B0: 監査ノードなしの既存動作、B1: START 1人でPreview→GO、B2: START 2～3人でPreview→GO、B3: Preview後のBBOX変更で旧GOが拒否、の順で確認します。B3は「upstream changed」「未承認State」「Structured layout changed」のいずれかで安全停止する場合があります。
