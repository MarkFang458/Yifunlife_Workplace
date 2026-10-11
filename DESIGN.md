---
name: "YIFUN Workplace V2"
description: "沿用亦玩深蓝金色、保留原生业务菜单的中文工作平台"
colors:
  primary: "#264b82"
  navigation: "#183765"
  navigation-active: "#315789"
  navigation-text: "#e4edf9"
  account-text: "#c4d2e6"
  gold: "#edbd0b"
  focus: "#b98500"
  canvas: "#f4f7fb"
  surface: "#ffffff"
  text: "#12233f"
  muted: "#586b84"
  line: "#dbe3ee"
  field-line: "#b9c7d9"
  table-head: "#f7f9fc"
  table-line: "#e6ecf4"
  hover: "#eaf1fb"
  notice: "#fff5d6"
  notice-text: "#6d5415"
  notice-line: "#ead59a"
  tag: "#eef3f9"
  tag-text: "#3a5272"
  done: "#e7f3ec"
  done-text: "#285c40"
  danger: "#953b35"
typography:
  body:
    fontFamily: "\"PingFang SC\", \"Microsoft YaHei\", Arial, sans-serif"
    fontSize: "14px"
    lineHeight: 1.55
  display:
    fontSize: "32px"
    fontWeight: 650
    lineHeight: 1.4
  headline:
    fontSize: "26px"
    fontWeight: 650
    letterSpacing: "-0.5px"
  title:
    fontSize: "20px"
    fontWeight: 650
  section:
    fontSize: "16px"
    fontWeight: 650
  summary:
    fontSize: "28px"
    fontWeight: 600
  table:
    fontSize: "13px"
  caption:
    fontSize: "12px"
  label:
    fontSize: "11px"
  mono:
    fontFamily: "ui-monospace, monospace"
    fontSize: "12px"
rounded:
  badge: "4px"
  field: "5px"
  control: "6px"
  panel: "8px"
  dialog: "10px"
  login: "12px"
spacing:
  compact: "8px"
  control: "12px"
  regular: "16px"
  form-gap: "18px"
  panel: "22px"
  page: "30px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "8px 15px"
  button-primary-hover:
    backgroundColor: "{colors.navigation}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.control}"
    padding: "8px 15px"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    rounded: "{rounded.control}"
    padding: "6px 8px"
  field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.field}"
    padding: "9px 11px"
  navigation-item:
    backgroundColor: "transparent"
    textColor: "{colors.navigation-text}"
    rounded: "{rounded.field}"
    padding: "10px 12px"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
  tag:
    backgroundColor: "{colors.tag}"
    textColor: "{colors.tag-text}"
    rounded: "{rounded.badge}"
    padding: "2px 7px"
  center-topbar:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    padding: "6px 18px"
---

# Design System: YIFUN Workplace V2

## Overview

**Creative North Star: "Operate · 亦玩工作台"**

沿用已确认的 Operate 方向：以中文业务名称、项目编号、员工身份和直接操作组织工作。深蓝导航、少量品牌金色、白色表格与清楚的分隔线构成视觉主体；使用已有品牌标志，不增加装饰图像或动效。

本记录于 2026-09-12 按统一品牌要求更新。workplace-theme.css 是 Workplace、报价、采购与售后的共用颜色和字体来源；workplace-logo.png 是共用完整标志。各中心保留原生菜单、专业布局与操作，使用同一深蓝导航、金色强调、中文字体和标题层级。构建时同步 Logo、网站图标和售后静态主题副本。产品边界见 PRODUCT.md。

**Key Characteristics:**
- 中文操作与可追溯编号优先。
- 深蓝导航、白色工作面、少量金色状态提示。
- 总入口展示完整导航，业务中心保留完整原生菜单。
- 移动端保留姓名、岗位与退出入口。

## Colors

主色用于操作按钮和链接，navigation 用于侧栏、登录品牌面与临时消息；navigation-active 和金色内嵌标记共同表示当前平台入口。金色不承担正文颜色。品牌图片置于白色衬底，保证原有深色字标清晰。

canvas、surface 和 line 通过浅色画布、白色工作面及细线建立层次；field-line 明确输入边界。muted 用于说明文字，table-head 与 table-line 区分表头和数据行。待处理标签与提示使用 notice / notice-text，完成或使用中标签使用 done / done-text，危险操作与错误文字使用 danger；普通标签使用 tag / tag-text。状态均有可读文字。

**The Status Text Rule.** 状态必须用文字表达，颜色只辅助辨认。

## Typography

正文采用 frontmatter 的本机中文字体栈；不加载外部字体。页面标题、面板标题与小节标题使用 headline、title、section，登录品牌标题使用 display。表格和项目选择器使用 table，说明与表头使用 caption，标签使用 label。汇总数字使用 summary 并启用等宽数字；金额右对齐，原始记录使用 mono 并允许断行。

桌面导航字重为 450，按钮为 600，表单标签及表头为 550。900px 以下汇总数字为 25px；640px 以下页面标题为 24px、登录标题为 27px。窄屏输入沿用当前字体尺寸，项目选择器为 13px；这里未声称已做移动端输入自动缩放处理。

## Layout

总入口桌面采用 204px 左侧导航与弹性主区；侧栏吸顶、高度为视口并可纵向滚动。主区最宽 1600px，页内留白使用 page；白色项目栏最小高 78px，选择器最大宽 400px。面板标题留白为 18px 22px，正文留白使用 panel。项目汇总是一条带分隔线的横向数据带。表格在自己的容器内横向滚动。

900px 以下导航缩为 164px，内容留白为 22px 18px，页标题及操作上下排列，项目栏隐藏辅助说明。640px 以下导航移至文档流顶部并横向滚动，分组标签隐藏；姓名、岗位和退出仍单独显示，退出按钮在身份区右侧。内容留白为 20px 14px，汇总每行两项，表格最小宽 580px，双列表单改为单列。项目选择器保留可访问标签，文字标签在视觉上缩小隐藏；刷新仍可操作。登录页在此断点由双列转为单列。

进入报价、采购、售后或财务中心后，总入口侧栏和项目选择栏收起，顶部保留“返回我的待办”、中心名称及桌面项目名称；售后和财务的子页面通过中心内导航切换。中心外壳占满 100dvh（100vh 回退），顶部最小高 56px；三个原生业务 iframe 充满其下剩余高度并独立滚动。640px 以下顶部隐藏项目名称，但保留返回和中心标题。内部员工返回我的待办，供应商返回个人账号。财务说明页使用相同紧凑顶部，在主区滚动。

## Elevation & Depth

主体没有悬浮阴影；层次来自导航色块、白色表面与单像素分隔线。当前导航的金色内嵌线是选中状态标记，不是卡片装饰。模态对话框以半透明深蓝遮罩分隔背景，临时状态消息固定在右下方。

## Shapes

组件使用 frontmatter 的小圆角层级：标签、字段、按钮、面板、对话框、登录品牌容器逐步加大。表格与汇总带保持平直边界。普通按钮最小高 40px，输入最小高 42px；移动页头操作、退出和中心返回按钮最小高 44px。表格中的紧凑文字按钮最小高 32px，不将其描述为全面满足触控尺寸要求。

## Components

- **导航与身份：** 平台导航有明确中文区域名，当前入口使用 aria-current。展示范围按角色及已授权中心确定；财务入口明确标为“未开放”。个人账号与退出在移动总入口继续可见，中心内账号菜单保持原生行为。
- **项目上下文：** 项目栏支持“全部项目”及“项目编号 · 项目名称”。中心顶部显示当前项目名称，修改项目须返回工作台。项目归属和服务端业务状态以实际数据为准。
- **原生中心边界：** 每个 iframe 具有中心标题，进入后仍显示该中心完整菜单。不要在平台外层重复渲染中心菜单，也不要通过嵌入样式隐藏中心自己的侧栏。保留原中心的专业布局和操作。报价及采购构建引入共用主题，售后加载启动时同步的主题副本；颜色、字体、Logo 和导航选中态以共用主题为准。模块专属布局继续由各自样式维护。手机售后完整显示标志，图标菜单保留可访问名称。
- **按钮与字段：** 主按钮深蓝白字，悬停加深；次按钮白底蓝字带边框，文字按钮透明底。次按钮与文字按钮悬停为浅蓝。禁用按钮透明度为 0.55。表单使用可见标签、原生 required / type 约束及明确提交文字；只读字段为浅色底。
- **键盘与反馈：** 外壳 focus-visible 使用 3px 金褐描边、偏移 3px；“跳至工作区”链接获得焦点时出现。进入中心把焦点移至返回按钮，离开中心移至可聚焦主区。对话框使用原生 showModal 和标题关联，关闭/取消后尝试恢复打开前焦点；提交期间禁用提交按钮，错误为 alert。登录错误同样为 alert，临时消息使用 polite 状态区域并在 6.5 秒后隐藏。外壳未引入动画，减少动态效果设置下保持普通滚动。
- **表格、标签与空状态：** 表头带 scope，编号和次级资料放在名称下方；行内按钮直接表述操作。空状态说明缺少什么及下一步，不用虚构数字填充。待处理、完成与普通标签保持短文字矩形。

以上为源码提取，非完整无障碍验收。qa/design-detector.json 生成时解析器不可用，使用降级正则扫描；其提示不构成完整对比度、键盘或业务流程结论。早期中心截图不作为当前紧凑中心布局的验证证据，当前实现需以本轮重新采集的截图及独立复核为准。

## Do's and Don'ts

- Do 保持中文业务名称、项目编号、员工身份和状态易读。
- Do 沿用深蓝、白色工作面及少量金色，使用已有品牌资源。
- Do 在移动总入口保留姓名、岗位、个人账号和退出入口。
- Do 让宽表格在局部滚动，让中心保留完整原生菜单。
- Don't 为单一中心复制新色板、替换 Logo 版本或引入另一套界面字体。
- Don't 用装饰图像、浮起卡片或动效替代业务信息。
- Don't 将“财务未开放”、待确认资料或未完成验收呈现为已完成状态。

三个原生业务中心在桌面（901px 起）共用 `--wp-center-nav-width: 208px`；报价编辑抽屉沿用原生小屏收起行为。此规则位于 workplace-theme.css，报价与采购须重建后生效，售后须同步静态副本。
