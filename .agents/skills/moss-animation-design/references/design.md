# 当前设计与可修改范围

以下是仓库所附版本的默认方案，不是电影官方运动规格。精确文件身份见根 `release.json`；最新用户要求优先于这些偏好。

## 基线与外观

- 成品是撤回透视试验后的正交版本。顶部细节已得到原设计者认可；“顶部点头比主体底部大”的观感仍未解决，不能登记为整体外观验收完成。
- 主壳、肩部、底部附件有固定实体几何；正面和上支架仍含原精细贴图/分层，属于混合模型，不是官方 CAD 或完整高保真实体。
- 暖白旧化表面、非对称结构、固定主眼、左侧状态指示灯是当前外观。两侧结构不能通过镜像交换。
- 已认可部分在无关修改中保持。若用户要求新材质、比例或表达，允许修改固定资产，不用历史偏好否定新目标。

## 控制器和输入

| 对象 | 可用控制 | 带动内容 |
| --- | --- | --- |
| `J5_lower_yaw` | 局部 Z 角度 | 下部机身整体回转 |
| `J3_body_pitch` | 局部 X 角度 | 机身、镜头、灯、底壳、线缆及J4一起俯仰 |
| `J4_lower_attachment_fold` | 局部 Y 角度 | 底部附件本体；不包括线缆 |
| `R3_body["indicator_level"]` | 亮度，当前0～1 | 左侧状态灯；主眼不参与眨眼 |
| `R3_body["scan_level"]` | 强度，当前0或0.24 | 固定半透明扇面 |

轴心、限位、J4坐标架和尺寸均为制作近似。当前发布模型不提供通用伸缩或导轨动画入口；不要凭旧分镜描述猜测它具备这些能力。`config/animation.json` 中 `yaw/pitch/fold` 单位为度，`warning` 选择状态灯红色材质。脚本按配置扩展单轴限位，不代表机械碰撞已验证。

## 默认场景

| 场景 | 当前行为 |
| --- | --- |
| 待机 | 回转0→12→24→24→12→0°，灯先后亮灭，主眼保持 |
| 悬停（row 4） | 机身摆正，J4为0/−10/0/+10/0°，指示灯1/0/1/0/1 |
| 输入关注 | 向下方向槽保持30°低头和扫描；这是静态槽，不是连续低头再扫描动画 |
| 左右拖动 | 机身原位静止，J4平贴机腹约130.1166°，左灯稳定红色，两方向16格同姿 |

其余行的参数直接以配置为准，不凭状态英文名称重新发明动作。当前方向行保留了七个相同的低头扫描槽，未实现所有方向的完整独立语义；恢复同版本应保留，修改方向能力则需单独验收。

## 判断修改是否合格

**硬约束**：同一动画内几何和所属关节关系固定；轴承连接不跳动；非对称结构不镜像；模型和图集不出现裁切、接缝残影或不透明内部缺口。

**默认指导**：机械动作沉稳、清楚，避免弹性呼吸与动物式眨眼。幅度、材质、灯光表达允许按用户目标调整，用原尺寸、原速结果判断，不以数值大小代表自然。

**能力边界**：素材无法保证客户端中断续播、扫描一次后关闭、拖动永久保持等时序。预览中的保持时长必须标明是演示；不要靠修改客户端程序实现这些承诺。

## 渲染与合成

在仓库根目录执行。需要 Python 3.10+、Pillow 和 Blender；已验证 Blender 5.2.2 LTS。`blender` 需在 PATH 中，或替换为本机可执行文件路径。

```bash
python -m pip install -r requirements.txt
python scripts/assemble_atlas.py --check MOSS.png

# 修改配置后，只替换悬停行，其他格保持原 PNG 像素
blender --background --python scripts/render_atlas.py -- --rows 4 --out build/hover-frames
python scripts/assemble_atlas.py --frames build/hover-frames --base MOSS.png --out build/MOSS-hover.png

# 修改共享模型后，全量渲染
blender --background --python scripts/render_atlas.py
python scripts/assemble_atlas.py

# 从发布 PNG 生成 11 个展示 GIF
python scripts/make_previews.py
```

| 脚本 | 输入 | 输出 / 检查 |
| --- | --- | --- |
| `render_atlas.py` | `--model`、`--config`、`--rows`、`--out` | 帧 PNG 和 `render.json`；检查网格、关节绑定、固定部件和相机 |
| `assemble_atlas.py` | `--frames`、可选 `--base`、`--out`，或 `--check` | v2 图集、检查报告、九个状态 GIF 和全格预览 |
| `make_previews.py` | `--atlas`、`--out` | 11 个展示 GIF；默认写入 `assets/previews/` |

默认定制输出为 `build/MOSS-custom.png`；`build/` 是可重新生成的工作目录，已被 Git 忽略。局部渲染合成必须提供 `--base`。原 `MOSS.png` 不会被默认覆盖；全量重渲染不保证与成品逐像素一致，因为成品制作包含局部像素保留与合成。

6 张贴图均已打包在 `assets/model/MOSS.blend` 内，无需外置副本。需编辑独立纹理文件时，可在 Blender 的 File → External Data → Unpack Resources 中解包。

图集为 8 列 × 11 行，每格 192 × 208；73 个使用格、15 个透明空格。前九行帧数为 `6,8,8,4,5,8,6,6,6`，最后两行各含八个静态方向槽。`durations_ms` 仅控制本地预览时序，不修改客户端播放速度；扫描和方向槽 GIF 的切换时长是演示。
