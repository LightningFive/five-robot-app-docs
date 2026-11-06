# 五号机器人 XApp SDK

**SDK 2026.11.05.5 · API 2.17 · XApp 包格式 1**。新增 Wi-Fi 与 BLE 外设共存、WSS、受限 HTTP/WS 请求头和双向 Opus。新接口已在 2.0.32 / API 2.17 配套固件验收。开发资料可从下方 Git 镜像取得，设备系统更新以官方渠道为准。[API 2.17 合同](docs/api-2.17.md) · [无线共存指南](docs/wifi-ble-coexist.md)。

制作设备主题：先读[主题 AI 制作入口](docs/theme-ai.md)。把入口中的一句话加上风格需求发给 AI，按公开数据合同制作原生 240×240 预览、`.xtheme`、源码和验证记录。主题资料独立修订，见[主题机器索引](docs/themes/index.json)与[可复制纯文本](docs/themes/prompt.txt)。

开发独立 ESP-IDF 原生固件：先读[原生固件 AI 入口](docs/native-firmware-ai.md)，只需把需求连同文档链接发给 AI。入口按需导向接线、电源、屏幕、音频、网络、内存、构建、镜像恢复及故障自查共十个专题，附[机器目录](docs/native/index.json)与 `tools/native_context.py`；不必一次读完整资料库。目标是完整独立工程和 `.bin`，资料不是已验收的通用 BSP。以下为安装在官方系统内的 XApp SDK。

设备为 ESP32-C3，240×240。API 2.16 及以前的结构和导入保留兼容。AMBE 实验功能默认关闭，DMR 0.1.1 仅支持连接测试。[API 2.16 合同](docs/api-2.16.md)。

[GitHub](https://github.com/LightningFive/five-robot-app-docs) · [Gitee](https://gitee.com/yorium/five-robot-app-docs) · [官方版本索引和 SDK 下载](https://site.flashbot5.com/developer/v1/index.json) · [安装工作台](https://site.flashbot5.com/install)

API 2.17 开发固定 Git 标签 `sdk-2026.11.05.5`，整套使用同一发行的头文件、工具和示例。安装 2.17 应用前，确认设备已运行支持 API 2.17 的配套固件。

上一版资料见 [2026.10.30.1 发行说明](docs/release-2026.10.30.1.md)。

## 开始

Python 3.10+；六套模板使用已校验的原生资产缓存，只需要 Python 标准库，不必先装字体/图标处理库。

```sh
python tools/workflow.py prepare --app work/my-app --id my-app --name "My App" --template native-ui --capabilities ui --inline-context
# 使用响应内的上下文和模板源码，编写业务及相关测试后：
python tools/workflow.py build --app work/my-app
```

环境、缺项准备、资源缓存、构建、最终包检查、APP 测试与源码交付由工具自动完成；不重复调用 doctor/validate/check_product/inspect。工具缺项才下载，支持 `--offline`。

## 给 AI 的复制入口

[复制 API 2.17 固定版本提示词](docs/xapp-prompt.txt)。仍可通过下方提示词使用官网索引提供的版本。

```text
按 https://site.flashbot5.com/developer/v1/index.json 对应 SDK 的 docs/ai-workflow.md 开发 XApp：【需求】。
```

[精简执行入口](docs/ai-workflow.md)按实际能力返回真实声明和规则。完整规则保留在 [ai-reference.md](docs/ai-reference.md)。源码齐全的集成可一次提交 JSON 请求从创建到交付，详见[自动化接口](docs/workflow-automation.md)。

## 开发包内容

| 内容 | 用途 |
| --- | --- |
| [公开头文件](sdk/xapp/x622_xapp.h) | API 2.17 声明与结构，保留旧 ABI |
| [基础交互](examples/hello/README.md) | 启动键松手、菜单、明确退出、绘制失败处理 |
| [原生动画 UI](examples/native-ui/README.md) | 稳定节点、缓存预算、原生插值、退出释放 |
| [原生音画 UI](examples/native-ui-audio/README.md) | 可见首屏、中键动作、双轨 PCM 与退出清理 |
| [中文资源](examples/resources-zh/README.md) | 原创中文笔画底图、包内资源、条带读取 |
| [异步联网](examples/http/README.md) | Wi-Fi/HTTP 状态、错误、超时、可退出 |
| [BLE 会话](examples/ble-session/README.md) | API 2.16 GATT 启停、状态、失败与退出 |
| [Wi-Fi 与 BLE 共存](docs/wifi-ble-coexist.md) | API 2.17 共存标志、最低版本、权限、启动和真机验收 |
| [API 索引](api.json) | 实际导入名/签名/权限/最低 API、生命周期和限制 |
| [工具锁文件](toolchain.lock.json) | 官方归档、固定版本、SHA256、支持平台 |
| `tools/workflow.py` | 用户自动准备、按能力上下文、一次构建交付、增量缓存和错误摘要 |
| `tools/doctor.py` / `bootstrap.py` | 环境诊断与可校验的工具准备 |
| `tools/create_app.py` / `build.py` / `validate.py` | 创建完整产品、编译、打包、独立语义/ABI 验收 |
| `tools/check_product.py` | 从最终包复验图标、双语标题、字形及生命周期要求；validate --product 复用 |
| `tools/test_sdk.py` / `tests/` | 所有模板实编译与主机状态/失败路径测试 |
| [发行规范](docs/releases.md) / `tools/release.py` | 冻结文件白名单、可重复 ZIP、校验清单 |
| [SDK-SNAPSHOT.json](SDK-SNAPSHOT.json) | 头文件来源与公开工具文件指纹 |

还有 [API 手册](docs/api-reference.md)、[扩展导航](docs/api-extensions.md)、[内存约束](docs/memory-profile.md)、[清单格式](docs/manifest.md)、[验收要求](docs/testing.md)。

SDK 维护者及发行 CI 运行 `python tools/test_sdk.py` 完整检查，普通 APP 任务不重复运行。构建报告包含最终 WASM 的 imports/exports；清单可要求必须保留的回调和 API，避免事件被链接删除。无需导入没有使用的 random。

本 SDK 包含全部公开声明、构建和静态验收工具；编译器按锁文件单独下载，不把数百 MB 的工具二进制塞入 Git。中文启动器/字体转换才需要可选 Pillow/fontTools 和已获授权字体。

XApp 是 freestanding C/C++ → wasm32，安装包为 `.xapp`；不运行 ESP-IDF、Python、JS，也不能把 `.bin` 改名当应用。
静态与主机桩测试不执行真实设备服务，报告的 runtime_tested/hardware_tested 保持 false，真机验收须单独记录。
不含私有固件、驱动/宿主模拟器、网站后端、部署配置、账号数据或 OTA 密钥。
