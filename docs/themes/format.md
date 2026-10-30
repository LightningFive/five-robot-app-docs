# 格式与公开工具

本页是制作导航，实际边界以同修订的校验器为准：[theme_tool.py](../../tools/theme/theme_tool.py)、[theme_presentation.py](../../tools/theme/theme_presentation.py)、[theme_native_scene.py](../../tools/theme/theme_native_scene.py)。结构摘录：[theme_format.h](theme_format.h)、[theme_layout.h](theme_layout.h)。这些是公开的数据合同，不含驱动或宿主实现。

## 项目输入

推荐从[未完成的主题骨架](../../examples/theme-starter/README.md)复制工程。打包入口：

```sh
python tools/theme/pack.py --project work/my-theme/theme.json --output work/my-theme/dist/my-theme.xtheme
```

`theme.json` 例子中的 `resources` 仅演示条目形状，实际必须补齐下节列出的资源：

```json
{
  "schema": "x622-theme-project/v1",
  "id": "my-theme",
  "name": "主题名称",
  "version": "1.0.0",
  "engine_abi": 2,
  "appearances": 2,
  "layout": "layout.json",
  "presentation": "presentation.json",
  "resources": [
    {"id": "0x100", "format": "A8", "path": "assets/volume.png"},
    {"id": "0x900", "format": "Font", "path": "assets/title.fnt2"}
  ]
}
```

- ID 为 1..31 个小写 ASCII 字母、数字、`_`、`-`，首字符字母或数字；名称 UTF-8 少于 48 字节，版本少于 16 字节。所有资源路径相对工程，不允许逃出目录。
- `appearances`：1 深色、2 浅色、3 两者。资源 `flags`：0 共享、1 仅深色、2 仅浅色；使用 3 表示两者也会按掩码校验，不能与同 ID 的共享/重叠资源重复。
- `layout` 指向 LYT1 的 JSON。`dark`/`light` 颜色均为 0..16777215 的整数；字段顺序在 [layout_codec.py](../../tools/theme/layout_codec.py)。这是固定字段模式，不能自行追加页面枚举或 LVGL 对象。
- PNG 自动读取原生尺寸；原始 `.bin` 必须提供整数 `width`、`height`。RGB565 均为小端。A8 读取 PNG 的 **alpha 通道**，不是灰度亮度；不透明白底 PNG 会得到实心遮罩，应先正确生成透明底。
- `RGB565A8` 每像素交错为 `RGB565LE + alpha`，共 3 字节；不是两块独立平面。`RGB565` 只接受不透明 PNG，透明图改用前者，不能默默丢弃透明度。
- 字体资源使用 `Font` 和 FNT2 文件。它只允许 ABI2 的 `0x900..0x907`，宽高为 0，深浅共享。
- ABI1 不设 `presentation`；ABI2 必须提供它。ABI3 只提供 `layout` 与 `native_scene`（已编译的 `.nscene`），不能同时塞入 ABI1/2 的图片资源和 STY2。

工具先完整校验，成功后才替换输出包。失败时不覆盖上一个有效包。报告包含包 SHA-256、主题 ABI、资源数和大小；`hardware_tested`、`visual_verified`、`performance_measured` 默认 false，不能手工改成通过。

## ABI1/2 资源表

每个声明支持的外观，都必须有下列资源，或由 `flags=0` 的共享资源满足。以校验器的 `REQUIRED_IMAGES` 为完整列表，不因某个当前页面不显示就删除兼容资源。

| ID | 内容 |
| --- | --- |
| `0x100..0x116` | Volume、Wifi、Bluetooth、Language、Palette、Package、Info、Flask、Back、Phone、Search、Lock、Refresh、Play、Signal、Display、Chip、Controller、Audio、Usb、Storage、Settings、Clock |
| `0x117` / `0x118` / `0x119` | 可选扩展：Trash／已安装更新图标保留槽／Store；商城与安装、卸载要可辨 |
| `0x201..0x20b` | Standby、Empty、Phone、Lan、Usb、Bluetooth、Power、Error、Success、Connecting、Screensaver 的兼容插画槽 |
| `0x300..0x309` | VolumeFrame、VolumeTrack、VolumeThumb、VolumeSpeaker、TimeoutDown、TimeoutUp、Wifi0、Wifi1、Wifi2、Wifi3 |
| `0x400`、`0x402`、`0x403` | 电池框、电池填充、充电标志；`0x401` 电池端子可选 |
| `0x500`、`0x501`、`0x502` | 状态用选中圆点／空心圆点／编辑标记 |
| `0x505` | 浅色外观额外要求的明暗预览图 |
| `0x600 + ASCII(字符)` | `0123456789:-` 时钟字形，每个字符独立资源 |
| `0x800 + ASCII(字符)` | 可选独立大号主页时钟；一旦使用必须提供整组 |
| `0x900..0x907` | ABI2 可选字体：Title、Value、Header、Body、Hero、Date、Keyboard、Status |

`0x200` 是禁止写入的品牌槽。相同 ID 可在互不重叠的深/浅外观中各有一条，不得重复共享或重叠。所有资源连续排布、有 CRC，不能带未索引的附加文件。

## 布局与样式

LYT1 固定 2968 字节：头部、深/浅各 33 色、32 个 metrics、8 个全局元素、32 个基础页面各 10 个槽。页面 `Content`/`Title` 与全局元素是屏幕坐标，其它槽在对应内容区的局部坐标。不能把设计图上的绝对坐标原样塞进所有局部槽。

基础内置字体尺寸仅允许 12、16、18、20、28。需要其它字形大小时使用合法字体角色及 STY2，不把 24 等未支持值塞进 LYT1 的内置字体 metrics。行高 40..60，header 24..72，所有矩形必须在合同边界内；Wifi/Battery 不得离屏，电池填充不能超出电池框。完整范围由 `verify_layout` 检查。

STY2 输入示例：

```json
{
  "schema": 1,
  "easing": "ease-out",
  "styles": [
    {"component": "RowTitle", "state": "Focused", "text": "#FFFFFF"},
    {"component": "Row", "state": "Focused", "background": "#174E86", "radius": 8}
  ],
  "pages": {}
}
```

组件、状态、页面、字体角色的真实名称在 `theme_presentation.py`，不能编造。STY2 最多 4096 字节、64 条样式、12 个页面槽位扩展；样式可以全局复用，不等于只能给 12 页换色。支持 `linear`、`ease-in-out`、`ease-out`；新主题优先使用后两种，保留宿主关闭动效能力。

## 字体生成

处理字体才安装 Pillow 与 fontTools，安装一次即可：

```sh
python -m pip install Pillow fonttools
python tools/theme/font.py --font work/my-theme/assets/allowed-font.ttf --characters work/my-theme/characters.txt --license work/my-theme/licenses/font-license.txt --size 18 --output work/my-theme/assets/title.fnt2
```

工具检查字体真实名称、缺字和 FNT2 边界，缺字直接失败；不会静默替换字体。默认按项目规范拒绝 Noto Sans SC 别名，不打包/下载未授权字体。许可文件和来源由制作者提供，工具记录许可哈希不构成授权证明。

每个 FNT2 子集最多 1024 字形、256 KiB，字形最多 64×64，行高 8..64。按实际 UI 文案、数字、符号和字号分角色准备；用户输入的任意 Unicode 不可能由一个小子集全覆盖，须检查目标宿主的回退行为并如实说明。APP 名称优先采用 APP 自带字形，不通过补全全局大字库解决。

## 包格式与 ABI3

所有整数小端。XTHM 头 256 字节，资源目录每条 32 字节；头部 CRC32 覆盖前 252 字节，SHA-256 覆盖头之后的全部目录和数据，每条资源另有 CRC32。包总长最多 4 MiB，顶层最多 256 条资源，单图最多 240×240。文件大小、头/索引范围、UTF-8、引用、外观、资源 CRC/SHA 都必须同时有效。

ABI3 顶层严格只有 LYT1 与 NSC1 两条资源。NSC1 包含有界图片、RLE、字体、文本绑定和元数据；当前验证器要求 93..128 个场景、最多 512 素材，每场景最多 128 个节点/文本绑定，字形必须符合缓存边界。具体节点字段在公开 `theme_native_scene.py`，不能直接调用宿主 C++ 或给场景添加执行代码。

本次提供 ABI3 **校验与封装**，没有把私有宿主、90 页的历史稿件、专用场景编译器或真实系统模拟器公开。缺少这些能力时选 ABI2，或明确停在 ABI3 设计候选；不能使用假场景、重复截图或修改校验器绕过绑定要求。
