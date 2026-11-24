# 模型评测实验室 · model-eval-lab

同一批题目、同样的提示词交给不同模型跑，提示词与产出原样归档，方便横向对比、复查和复现。

## 目录结构

```text
01-svg/            01–03          SVG 生成
02-threejs-webgl/  04–09、21–23   Three.js / WebGL 场景
03-blender/        10–13          Blender 建模与脚本
04-games/          14–20          网页游戏
```

每个任务目录内部约定：

- `prompt.zh.txt` / `prompt.en.txt`：中英双语提示词，两版内容一致；
- `<模型版本>/`：该模型的原样产出，如 `glm-5.4/`、`glm-5.3-flash/`、`deepseek-v4.1-flash/`；
- 参考图放在 `reference/`（Blender 类任务）或分类目录的 `references/` 下，同一轮对比共用同一组图片。

02、03、09、15、16 等属于批量题：提示词按行逐条发送，开头方括号内是发送方式的说明，不改动原文。

## 任务索引

| # | 任务 | 类型 | 产出 |
|---|---|---|---|
| 01 | 鹈鹕骑自行车 | SVG | 全部 |
| 02 | 动物做某事（30 条） | SVG | — |
| 03 | 动物 × 载具（48 条） | SVG | — |
| 04 | 三维鹈鹕（WebGL） | WebGL | 全部 |
| 05 | 霓虹赛车 | WebGL | 全部 |
| 06 | 街机赛车（完整规格） | WebGL | 全部 |
| 07 | 太阳系 | WebGL | — |
| 08 | Yonkers 机甲（需 OSM 数据） | WebGL | — |
| 09 | 黑洞 / 路径追踪 / 流体（3 条） | WebGL 着色 | — |
| 10 | 鹈鹕三步建模 | Blender | — |
| 11 | 图像→模型：法贝热彩蛋 | Blender | — |
| 12 | 单次 bpy 脚本重建 | Blender | glm-5.3-flash、glm-5.4 |
| 13 | 渲染–精修–MCP | Blender | — |
| 14 | 飞行游戏 | 游戏 | — |
| 15 | 开放题（2 条） | 游戏 | — |
| 16 | 街机 Doom（3 档难度） | 游戏 | — |
| 17 | 巨龙国度 | 游戏 | — |
| 18 | 战斗法师 | 游戏 | — |
| 19 | /swarm 多智能体 | 游戏 | — |
| 20 | Tree appreciator / 浣熊劫案 | 游戏 | — |
| 21 | 诗句：明月松间照，清泉石上流 | WebGL | 全部 |
| 22 | 诗句：大漠孤烟直，长河落日圆 | WebGL | — |
| 23 | 诗句：孤舟蓑笠翁，独钓寒江雪 | WebGL | — |

「全部」指 `deepseek-v4.1-flash`、`glm-5.3-flash`、`glm-5.4` 三个模型；「—」表示目前只提交了提示词，产出待补。21–23 为本仓库新增的诗句系列。

## 查看产出

- **SVG**：浏览器直接打开 `.svg` 文件。
- **网页**：双击对应目录下的 `index.html`。多数页面从 CDN 加载 three.js，联网即可运行；`02-threejs-webgl/05-neon-racer/deepseek-v4.1-flash/` 是完整工程，自带 bundle、字体与第三方许可证。
- **Blender**：在 Blender 5.0 中执行脚本，例如

  ```sh
  blender --background --python 03-blender/12-bpy-one-shot/glm-5.4/out.py
  ```

## 已评测模型

| 目录名 | 说明 |
|---|---|
| `deepseek-v4.1-flash` | DeepSeek |
| `glm-5.3-flash` | 智谱 GLM |
| `glm-5.4` | 智谱 GLM |

## 参考素材

- `03-blender/12-bpy-one-shot/reference/cat-robot-4k.png`：12 号任务的共用参考图；
- `03-blender/references/zhipu-character/`：同一角色的多视角参考图，供图像→模型类任务共用。

## 说明

- 产出按模型原始输出归档，仅做必要的可运行性修补，不改动题意。
- 任务 01–20 沿用原清单，21–23 为本地新增；批量题的开头说明保留了原文措辞。

## 贡献者

- dandan1232
- aut-rain

## 许可证

本项目采用 [MIT 许可证](LICENSE)。
