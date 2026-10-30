# 主题输入骨架

这是未完成的 ABI2 输入，不含私有原稿、品牌图、字体二进制或一套伪装成品的通用图标。

复制本目录到 `work/my-theme`，保留 LYT1 字段名，按批准的原生设计调整布局/调色板，填写真实 ID/名称与 `presentation.json`，生成本主题的透明资源和必要字体子集，按[格式表](../../docs/themes/format.md)补齐 `theme.json.resources`。

```sh
python tools/theme/pack.py --project work/my-theme/theme.json --output work/my-theme/dist/my-theme.xtheme
```

空资源列表会被拒绝，这是正常的制作守卫。不要把测试中的 1 像素夹具、示例数值、同一图形填满所有槽位或缺字字体作为交付。

完整开发入口：[theme-ai.md](../../docs/theme-ai.md)。
