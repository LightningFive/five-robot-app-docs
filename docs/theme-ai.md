# X622 主题：AI 制作入口

资料修订：`theme-2026.10.30.1`。适用于五号机器人 X622 的 240×240 屏幕，交付可安装的 `.xtheme`、完整源工程和原生像素预览。本入口与 XApp、独立 `.bin` 固件分开；主题是数据，不运行代码。

## 用户只需复制这一句

```text
读取 https://raw.githubusercontent.com/LightningFive/five-robot-app-docs/main/docs/theme-ai.md ，按规范为五号机器人制作完整可安装的主题，交付240×240预览、主题包和源码；需求：【填写你的风格或设计要求】。GitHub读取失败时改读 https://gitee.com/yorium/five-robot-app-docs/raw/main/docs/theme-ai.md 。
```

## AI 第一次执行

1. 阅读本文和[主题制作合同](themes/development.md)。再按需要读取[格式与工具](themes/format.md)、[视觉与验收](themes/acceptance.md)，不默认下载固件、XApp 工具链或整套字体库。机器目录与 SHA-256 在 [themes/index.json](themes/index.json)。
2. 已有本仓库就复用。否则浅克隆一个可用镜像一次，固定本次 commit 和资料修订；GitHub 一次失败切 Gitee，不在失败地址反复重试：

   ```sh
   git clone --depth 1 https://github.com/LightningFive/five-robot-app-docs.git five-robot-sdk
   # GitHub 不通时，用 https://gitee.com/yorium/five-robot-app-docs.git 代替同一条命令的仓库地址。
   cd five-robot-sdk
   python tools/theme/context.py --check
   ```

   无法克隆但能读取 raw 时，按 index 的白名单获取所需文件并校验；全部工具不可得时明确说明缺口，不能交伪包或宣称已打包。
3. 默认中文、清爽清晰、图标语义明确、四项列表、非线性选中动画。主题只改变外观，保留现有中键确认、左键返回、上下翻动及系统业务；不编辑固件、API、分区、音频或 XApp 运行内存管理。
4. 有设计稿则以批准的原生稿为依据；只有风格描述时，先制作 240×240 全套组件稿，自查对齐、字形、透明边缘和所有状态，再按稿实现。用户明确要求先审图时先交原生稿，未经批准不声称稿件已批准。
5. 普通主题默认 ABI 2：组件布局、字体、状态样式和动态内容由现有系统承载，兼顾新旧主题引擎。ABI 1 仅用于明确的旧设备兼容；ABI 3 仅在确有匹配的 NSC1 编译/渲染能力时选择，不能为省事把页面截图塞进场景。先核对目标设备的 `theme-abi/N` 能力，不拿 XApp API 2.16 代替主题 ABI。

## 制作到交付

- 复制 `examples/theme-starter/` 到当前主题工程，修改 `theme.json` 的 ID、名称、版本、appearance、布局和样式，编写本主题的资源生成器。模板是未完成的输入骨架，缺少资源时构建会失败，不是改个名字就能交付的成品。
- 逐组件制作透明图标、插画、时钟数字和必要字体子集，复用同一资源和颜色角色；不得用整屏截图、示例文字、电量数值或进度数值代替实时系统内容。品牌 Logo 与二维码由系统提供，不放进主题资源槽。
- 完成需求和自查后只执行一次常规打包，工具内已完成格式、布局、引用、CRC 与 SHA 校验，不再重复跑同一套检查：

  ```sh
  python tools/theme/pack.py --project work/my-theme/theme.json --output work/my-theme/dist/my-theme.xtheme
  ```

  处理 PNG 时才需要 Pillow。原始 `.bin` 数据及打包/校验只用 Python 3.10+ 标准库；不要求安装 ESP-IDF、WASM 编译器或设备驱动。
- 遵守[视觉与验收清单](themes/acceptance.md)。用户要求一比一时，应提供批准稿与真实渲染帧的逐像素对比；仅有自己生成的设计预览或包校验不能算一比一。没有设备权限时交候选包，实机、声学、帧率保持未测。
- 交付 `dist/<id>.xtheme`、`*.validation.json`、源码 ZIP、可复现生成/打包命令、字体/图标许可，以及 `previews/` 下的原生 240×240 PNG、状态总览和覆盖表。简要说明主题 ABI、深浅模式、已测项目与限制。不自动安装、烧录、擦除或发布到商城。

## 必须守住的质量线

- 图标要有透明底且抠干净，边缘无底色和杂线，使用透明轮廓的光学中心；安装、商城、卸载用不同图标。
- 电量文字与电池图标垂直居中且紧邻；Wi-Fi 未点亮的格子为灰色。时间、信号、充电、电量、安装进度、容量、应用名都是真实绑定。
- 中文字体默认遵循现有 SDK 的 HarmonyOS Sans SC 方向；仅使用获授权字体。不得静默用 Noto Sans SC 或其它缺字/替代字体糊弄，不把 2 万汉字整库塞进主题。应用名字优先使用 APP 自带资源，主题不能要求重打包所有 APP。
- 不换按键逻辑，不复活屏保、旧 OTA 入口、返回行等已删除的系统流程；受保护或当前协议不能换皮的页面保留系统实现并列出边界。
- 用组件复用、局部刷新和已有缓存预算追求流畅；不加全屏双缓冲，不每帧读字体/图标，不改音频和 XApp 内存，不靠关背光掩盖刷新。不把主机耗时倒数写成真机 60 FPS。

详细合同：[development](themes/development.md) · 格式/工具：[format](themes/format.md) · 验收：[acceptance](themes/acceptance.md)。这些资料与打包工具是公开制作资料，未改变固件或 XApp API，也没有替本次主题完成实机验收。
