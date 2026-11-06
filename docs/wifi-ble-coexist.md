# Wi-Fi 与 BLE 共存

SDK 2026.11.05.5 的 Git 标签为 `sdk-2026.11.05.5`。设备需要支持 **API 2.17**。配套系统 2.0.32 已在原生 USB 新板和 CH343 旧板验收。

1. 在 `app.json` 中设置 `api_major: 2`、`api_minor: 17`。同时申请 `X622_PERMISSION_WIFI_CONNECT` 和 `X622_PERMISSION_BLE_ADVERTISE`（共 `0x120`）。HTTP 业务还需申请 `X622_PERMISSION_NETWORK_HTTP`，并保留模板及实际使用功能的权限。共存标志复用 `ble_open` 的结构，单凭导入名只能推导到 2.16。
2. 在版本化 `x622_ble_config_t` 中设置 `version = X622_BLE_CONFIG_VERSION`、`size = sizeof(config)`，完整填写实际角色的描述符。对 `flags` 按位加上 `X622_BLE_COEXIST_WIFI`，用 `x622_ble_open(&config, sizeof(config))` 开启 BLE 外设。GATT 流使用三个不同的非零 UUID。见[会话结构](../sdk/xapp/x622_ble_session.h)与 [BLE 基础示例](../examples/ble-session/README.md)。
3. 在首屏就绪后显式调用 `x622_wifi_start()` 连接系统已保存的 Wi-Fi。两项服务可分别启动和停止。通过 `x622_wifi_status`、`x622_ble_status` 分别确认就绪。第二项启动失败时保留已正常运行的第一项，按业务决定何时重试。
4. 用异步轮询处理连接、订阅、队列忙和断线，限制待发数据。退出时分别调用 `x622_ble_stop()`、`x622_wifi_stop()` 释放本应用持有的服务。

准备工作流时选择 `ble,http` 或 `ble,net`，从同一 SDK 读取真实声明。参考[开发工作流](ai-workflow.md)。

共存覆盖普通 STA Wi-Fi 和版本化 BLE 外设会话。私有 Wi-Fi、网关、ESP-NOW 以及独立 Beacon 不在这项合同内。SDK 不提供 Bluetooth Classic、BLE 扫描或 Central。Wi-Fi 与 BLE 共享无线时隙，应用需自行验证并发负载、延迟和续航。

四台实机各验证了 64 个 20 字节的加密 BLE GATT 包精确回传，同一 BLE 会话就绪期间均收到 Wi-Fi HTTP 204。四台应用均正常退出，其中一台在 Windows 重连后单独通过。
