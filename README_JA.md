# MiniMax H3 Draft Continue — v1.1.1

**1枚見て、気に入ったら同じH3生成の続きへGO。既存WorkflowのSampler部分に挿入できます。**

## v1.1.1 互換性修正

ComfyUIでは標準 `BasicGuider` がExtension Loader側の別モジュールインスタンスから生成される場合があります。v1.1.0はPythonのクラス同一性を厳密比較していたため、通常のCore `BasicGuider`でもSampling前に拒否することがありました。v1.1.1では、対応するCore Guiderの契約/MROを検証し、Workflowから渡された実インスタンスをそのまま安全にsnapshotします。`BasicGuider` / `CFGGuider` / `DualCFGGuider`を対象とし、2モデルを持つGuiderや未知のCustom Guiderは専用Resume Adapterなしに推測して通しません。

## 接続用2ノード

| ノード | 入力 | 出力 |
|---|---|---|
| **H3 Draft Sampler** | `NOISE / GUIDER / SAMPLER / SIGMAS / LATENT` ＋ Preview用の映像VAE、停止step | `IMAGE / H3_SAMPLER_DRAFT_STATE / STRING` |
| **H3 Continue Sampler** | 確認済みStateとGO承認 | `LATENT (output) / LATENT (denoised_output) / STRING` |

```text
既存のMODEL + Turbo LoRA ──→ BasicGuider / CFGGuider ──┐
既存のCONDITIONING ─────────→ 同じGuider                 │
既存のNOISE / SAMPLER / SIGMAS / AV LATENT ─────────────┤
                                                     ▼
                                             H3 Draft Sampler
                                             1枚確認・途中停止
                                                     │ State
                                                     ▼
                                             H3 Continue Sampler
                                                     │ LATENT
                                  ┌──────────────────┴──────────────────┐
                                  ▼                                     ▼
                            既存VAEDecode                         既存VAEDecodeAudio
                                  └──────────────────┬──────────────────┘
                                             既存CreateVideo
                                                     ▼
                                             好みの保存ノード
```

**Prompt・CLIP・解像度・尺・CFG・LoRA・schedulerは元Workflow側で管理します。** 新ノードがPromptやconditioningを作り直すことはありません。Continueは標準LATENTを返すので、既存のDecode／後処理／保存へ接続できます。

従来の **H3 T2VA Draft / H3 T2VA Continue** も残しています。

## 操作

推奨Baselineは **4-step Turbo LoRA / strength 1.0 / Total 6 / Preview 3 / Euler / simple**。

1. **Preview**でFrame 0の完成予測を1枚確認。
2. NGなら **New seed + Preview**。
3. OKなら **GO · Continue this draft**。
4. 同じ途中AV latentから残りstepを実行し、通常のLATENTとして下流へ渡します。

GO時に新しいランダムノイズ、画像再エンコード、Prompt再生成、別LoRAへの切替は行いません。

## 既存Workflowへの組み込み

1. 元の `SamplerCustomAdvanced` へ入っている **noise / guider / sampler / sigmas / latent_image** をDraft Samplerの同名ポートへ接続。
2. MiniMax H3 Video VAEを `video_vae` へ接続。
3. `draft_state` をContinue Samplerへ接続。
4. 元Samplerの **output / denoised_output** から先をContinueの同名出力へ移す。

Reference、Guide、BBOX由来のStructured Promptは上流のnative conditioningへ含めます。標準H3のtensorベースReference/Keyframe conditioningは保持して渡します。live ControlNet/hook、noise_mask、独自/複数モデルGuiderは専用Adapterが必要です。

## 対応範囲

- native MiniMax H3 joint AV latent、batch=1
- Core BasicGuider / CFGGuider / DualCFGGuider
- **Core Euler / churn=0**
- 外部SIGMASをそのまま使用
- stateは同一ComfyUI backend session内のみ
- stateのCPU所有payload上限 512 MiB
- Previewはx0 estimate。現在は全動画フレームをVAE DecodeしてからFrame 0だけ残します

`res_multistep`等の履歴依存Samplerを勝手にEulerへ変更しません。対応外は明示エラーにします。

## 確認状況

Coreノードだけで行ったProof-of-Conceptでは、3/6 Preview → 残り3step Continue → 動画生成までユーザー確認PASS済みです。

v1.1.1では、ComfyUI_W実機で通常のCore BasicGuiderがv1.1.0の厳密class identity判定により拒否される問題を修正しました。ホスト回帰テストでは別ロードされた `Guider_Basic` を再現してPASSしています。v1.1.1修正後の実H3 GPU再実行で最終確認してください。
