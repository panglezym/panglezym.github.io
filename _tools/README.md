# 作品集维护清单

作品集站、个人主页 README、每个仓库的社交预览图都由同一份 `works.json` 生成，加作品或改文字只改这一份。`_tools/` 以下划线开头，GitHub Pages 不会发布它。

## 本地怎么放

把这两个仓库克隆到同一个父目录下，生成器会按相对位置找到主页仓库：

- `panglezym.github.io/`：作品集站和本目录
- `panglezym/`：个人主页 README，生成器会直接写进去

```bash
gh repo clone panglezym/panglezym.github.io && gh repo clone panglezym/panglezym
```

依赖：Python 3、Pillow、playwright（装好 chromium：`python3 -m playwright install chromium`）。

## 常用命令（在 panglezym.github.io 根目录跑）

```bash
python3 _tools/build.py shots hok     # 重截某个作品；不写名字就全截
python3 _tools/build.py build         # 生成页面、站点图、社交预览图、主页 README
python3 _tools/build.py all           # 先全截再生成
```

产物：`index.html`、`assets/`（站点用）、`_tools/social/<slug>.png`（要传到各仓库的预览图）、`../panglezym/README.md`。

## 加一个新作品

1. **作品仓库**：新建公开仓库，放单文件原型 `index.html`，有 PRD 也一起放，再按下面的模板写 README。
2. **About 栏**：填一句中英简介，Website 填它的 Pages 地址，加 5–7 个标签，统一带上 `chinese`。
3. **Pages**：Settings → Pages → 选 main 分支、根目录。等访问返回 200 再往下走。
4. **清单**：在 `works.json` 的 `works` 里加一条。字段照着已有的写：
   - `slug` 用短英文；`title` 太长时用 `title_lines` 指定断行。
   - `desc` 写两三句：做了什么、规模多大、仓库里有什么。
   - `shot` 写截图视口和步骤，步骤能用的有：`click_text`、`click_text_exact`、`js`、`scroll_y`、`scroll_to_block_of_text`，每步可以带 `wait` 和 `repeat`。
   - 没有网页的作品不写 `shot`，改写 `toc_card`，用一张目录页代替截图。
5. **截图**：`build.py shots <slug>`，然后打开 `_tools/shots/<slug>.jpg` 看一眼。要截原型里最能代表作品的那一屏，不要截登录页或空状态。
6. **生成**：`build.py build`。本地打开 `index.html` 看一遍，桌面宽度和手机宽度都要看。
7. **提交**：两个仓库分别提交、推送。作者只写 `赵永明 <panglezym@gmail.com>`，不带 Co-Authored-By。
8. **预览图**：把 `_tools/social/<slug>.png` 传到新仓库 Settings → Social preview。没有接口，只能在已登录的浏览器里传。
9. **回读**：站点返回 200；主页能看到新的一行；用 GraphQL 查 `usesCustomOpenGraphImage`，结果为 true。
10. **置顶**：值得置顶的话，在主页点 Customize your pins 自己换。

## 作品仓库 README 模板

```markdown
# 作品名 · English Name

> 一句话：解决谁的什么问题。

> 这是一个产品设计练习：仓库里是可交互的高保真原型（`index.html`）和 PRD，不含后端代码。文中的数字都是设计目标或原型里的示例数据。

**👉 [在线预览](https://panglezym.github.io/<仓库名>/)**

## 这是什么
## 关键设计取舍（为什么这么做、放弃了什么）
## 怎么看
- 在线预览：…
- 本地查看：下载 `index.html`，直接用浏览器打开
## 仓库里有什么
（照实列文件，不写不存在的目录、npm 命令、src 结构）
## License
仅供学习交流，转载请注明出处。© 赵永明
```

## 规矩

- 只放个人设计练习，不放任何雇主的材料或数据。
- 演示数据要写明是演示，不写成「当前值」「已上线」。
- 首页和预览图用原型真截图，不用插画。
- 置顶只放最好的四五个；弱的或过时的就归档，不删。

## 定期看一眼（每季度一次，或者要把链接发给别人之前）

- 各作品网页还能打开吗（`curl -s -o /dev/null -w "%{http_code}"` 每个 Pages 地址）
- 置顶是不是还是最好的那几个
- `works.json` 的 `lead`、`focus` 还贴不贴合现在的方向
