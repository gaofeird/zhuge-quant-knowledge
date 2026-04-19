"""
量化数据工具体系 - 示例代码
整合 MinerU + Crawlee + 量化技能

依赖安装:
    pip install mineru crawlee pandas langchain chromadb openai

使用方法:
    python examples.py
"""

import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict
import json

# ============================================================
# 示例1: MinerU PDF 解析
# ============================================================

def mineru_parse_example():
    """
    MinerU 解析研报 PDF 示例
    
    功能:
    - 解析 PDF 为 Markdown/JSON
    - 提取表格、公式、图片
    - 支持中文 OCR
    """
    try:
        from mineru import MinerU
        
        # 初始化解析器
        # backend: pipeline (CPU快速) / vlm (GPU高精度) / hybrid (混合)
        parser = MinerU(backend="pipeline")
        
        # 解析单个文件
        # result = parser.parse(
        #     input_path="report.pdf",
        #     output_path="./output/report",
        #     output_format="json"  # json / markdown
        # )
        
        # 批量解析目录
        # results = parser.parse(
        #     input_path="./reports/",
        #     output_path="./output/",
        #     output_format="json"
        # )
        
        print("✅ MinerU 初始化成功")
        print("   backend: pipeline (CPU模式)")
        
        return parser
        
    except ImportError:
        print("❌ MinerU 未安装，请运行: pip install mineru")
        return None
    except Exception as e:
        print(f"❌ MinerU 初始化失败: {e}")
        return None


def extract_financial_tables(parsed_content: dict) -> Dict[str, list]:
    """
    从解析结果中提取财务表格
    
    Args:
        parsed_content: MinerU 解析后的 JSON 内容
        
    Returns:
        分类后的财务数据字典
    """
    tables = {
        "income_statement": [],  # 利润表
        "balance_sheet": [],     # 资产负债表
        "cash_flow": [],         # 现金流量表
        "forecast": [],          # 盈利预测
    }
    
    for table in parsed_content.get("tables", []):
        title = table.get("title", "").lower()
        
        if any(kw in title for kw in ["利润", "损益", "income"]):
            tables["income_statement"].append(table)
        elif any(kw in title for kw in ["资产", "负债", "balance"]):
            tables["balance_sheet"].append(table)
        elif any(kw in title for kw in ["现金", "现金流", "cash flow"]):
            tables["cash_flow"].append(table)
        elif any(kw in title for kw in ["预测", "预计", "forecast"]):
            tables["forecast"].append(table)
    
    return tables


# ============================================================
# 示例2: Crawlee 爬虫
# ============================================================

async def crawlee_news_example():
    """
    Crawlee 财经新闻爬虫示例
    
    功能:
    - 采集财经新闻
    - 自动绕过反爬
    - 支持代理轮换
    """
    try:
        from crawlee.crawlers import BeautifulSoupCrawler, BeautifulSoupCrawlingContext
        
        # 初始化爬虫
        crawler = BeautifulSoupCrawler(
            max_requests_per_crawl=20,  # 限制请求数
        )
        
        news_list = []
        
        @crawler.router.default_handler
        async def handler(context: BeautifulSoupCrawlingContext):
            # 提取新闻列表
            # 注意: 选择器需要根据实际网站结构调整
            items = context.soup.select('.news-list .item')
            
            for item in items:
                news = {
                    "title": item.select_one('.title').get_text(strip=True) if item.select_one('.title') else "",
                    "url": item.select_one('a')['href'] if item.select_one('a') else "",
                    "source": item.select_one('.source').get_text(strip=True) if item.select_one('.source') else "",
                    "time": item.select_one('.time').get_text(strip=True) if item.select_one('.time') else "",
                }
                news_list.append(news)
            
            # 提取下一页链接
            next_page = context.soup.select_one('.pagination .next')
            if next_page:
                await context.enqueue_links()
        
        # 运行爬虫
        # await crawler.run(['https://example-finance.com/news'])
        
        print(f"✅ Crawlee 爬虫初始化成功")
        print(f"   已采集 {len(news_list)} 条新闻")
        
        return news_list
        
    except ImportError:
        print("❌ Crawlee 未安装，请运行: pip install 'crawlee[all]'")
        return []
    except Exception as e:
        print(f"❌ Crawlee 爬虫运行失败: {e}")
        return []


async def crawlee_stock_price_example():
    """
    Crawlee 股票行情爬虫示例
    
    功能:
    - 采集实时行情
    - 自动重试失败请求
    - TLS指纹伪装
    """
    from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
    
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=10,
        headless=True,
        browser_type='chromium',  # 或 'firefox'
    )
    
    prices = []
    
    @crawler.router.default_handler
    async def handler(context: PlaywrightCrawlingContext):
        # 等待页面加载
        await context.page.wait_for_load_state('networkidle')
        
        # 提取股票价格
        price_elem = await context.query_selector('.stock-price')
        if price_elem:
            price = await price_elem.text_content()
            prices.append({
                "code": context.request.url.split('/')[-1],
                "price": price,
            })
    
    # 运行爬虫
    # stock_codes = ['sh600519', 'sz000858', 'sh300750']
    # urls = [f'https://example-quote.com/{code}' for code in stock_codes]
    # await crawler.run(urls)
    
    return prices


# ============================================================
# 示例3: 完整数据流水线
# ============================================================

@dataclass
class PipelineConfig:
    """流水线配置"""
    # 路径配置
    raw_data_dir: Path = Path("./data/raw")
    parsed_data_dir: Path = Path("./data/parsed")
    output_dir: Path = Path("./data/output")
    
    # MinerU 配置
    mineru_backend: str = "pipeline"  # pipeline / vlm / hybrid
    
    # Crawlee 配置
    crawler_timeout: int = 30
    max_requests: int = 50


class QuantDataPipeline:
    """
    量化数据流水线
    
    整合数据采集、文档解析、数据分析全流程
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self._init_dirs()
        self._init_parsers()
    
    def _init_dirs(self):
        """初始化目录"""
        for dir_path in [
            self.config.raw_data_dir,
            self.config.parsed_data_dir,
            self.config.output_dir
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _init_parsers(self):
        """初始化解析器"""
        try:
            from mineru import MinerU
            self.mineru = MinerU(backend=self.config.mineru_backend)
        except ImportError:
            print("⚠️ MinerU 未安装")
            self.mineru = None
    
    async def collect_news(self, keywords: List[str]) -> List[Dict]:
        """
        采集财经新闻
        
        Args:
            keywords: 搜索关键词列表
            
        Returns:
            新闻列表
        """
        try:
            from crawlee.crawlers import BeautifulSoupCrawler, BeautifulSoupCrawlingContext
            
            crawler = BeautifulSoupCrawler(
                max_requests_per_crawl=self.config.max_requests
            )
            
            news_list = []
            
            @crawler.router.default_handler
            async def handler(context: BeautifulSoupCrawlingContext):
                # 提取新闻（需根据实际网站调整选择器）
                items = context.soup.select('.news-item')
                for item in items:
                    news_list.append({
                        "title": item.select_one('.title').get_text(strip=True) if item.select_one('.title') else "",
                        "url": item.select_one('a')['href'] if item.select_one('a') else "",
                        "crawl_time": str(context.request.loaded_url),
                    })
            
            # 搜索新闻
            for kw in keywords:
                url = f"https://search.eastmoney.com/news?s={kw}"
                await crawler.run([url])
            
            return news_list
            
        except ImportError:
            print("⚠️ Crawlee 未安装")
            return []
        except Exception as e:
            print(f"⚠️ 新闻采集失败: {e}")
            return []
    
    def parse_report(self, pdf_path: Path) -> Optional[Dict]:
        """
        解析研报 PDF
        
        Args:
            pdf_path: PDF 文件路径
            
        Returns:
            解析后的内容字典
        """
        if self.mineru is None:
            print("⚠️ MinerU 未初始化")
            return None
        
        try:
            result = self.mineru.parse(
                input_path=str(pdf_path),
                output_path=str(self.config.parsed_data_dir / pdf_path.stem),
                output_format="json"
            )
            return result.content
        except Exception as e:
            print(f"⚠️ PDF 解析失败: {e}")
            return None
    
    def extract_metrics(self, parsed_content: Dict) -> Dict:
        """
        提取财务指标
        
        Args:
            parsed_content: 解析后的内容
            
        Returns:
            财务指标字典
        """
        metrics = {}
        
        # 提取表格
        tables = extract_financial_tables(parsed_content)
        
        # 提取文本中的关键数据
        text = parsed_content.get("text", "")
        
        # 简单的正则提取示例
        import re
        
        # 提取评级
        rating_pattern = r"(买入|增持|中性|减持|卖出)"
        rating_match = re.search(rating_pattern, text)
        if rating_match:
            metrics["rating"] = rating_match.group(1)
        
        # 提取目标价
        target_pattern = r"目标价[：:]\s*(\d+\.?\d*)"
        target_match = re.search(target_pattern, text)
        if target_match:
            metrics["target_price"] = float(target_match.group(1))
        
        # 提取盈利预测
        forecast_pattern = r"(\d{4})年.*?净利润.*?(\d+\.?\d+)"
        forecasts = re.findall(forecast_pattern, text)
        if forecasts:
            metrics["profit_forecast"] = {
                year: float(value) for year, value in forecasts
            }
        
        return metrics
    
    def save_result(self, data: Dict, filename: str):
        """保存结果到文件"""
        output_path = self.config.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 结果已保存: {output_path}")


# ============================================================
# 示例4: 对接研报分析技能
# ============================================================

def analyze_with_skill(parsed_content: Dict) -> str:
    """
    使用研报分析技能进行分析
    
    注意: 这里需要对接实际已安装的研报分析技能
    """
    # 伪代码示例
    """
    from skills.research_report_analyzer import ResearchReportAnalyzer
    
    analyzer = ResearchReportAnalyzer()
    
    analysis = analyzer.analyze(
        title=parsed_content.get("title"),
        content=parsed_content.get("text"),
        tables=parsed_content.get("tables"),
        charts=parsed_content.get("images")
    )
    
    return analysis
    """
    
    # 返回示例结果
    return f"""
# 研报自动分析摘要

## 核心观点
基于自动提取的研报内容生成本摘要。

## 财务摘要
- 提取的表格数量: {len(parsed_content.get('tables', []))}
- 提取的图片数量: {len(parsed_content.get('images', []))}

## 风险提示
[需对接研报分析技能进行详细分析]
"""


# ============================================================
# 运行示例
# ============================================================

async def main():
    """运行完整示例"""
    print("=" * 60)
    print("量化数据工具体系 - 示例演示")
    print("=" * 60)
    
    # 示例1: MinerU 初始化
    print("\n[1/4] MinerU 示例...")
    mineru_parse_example()
    
    # 示例2: Crawlee 爬虫
    print("\n[2/4] Crawlee 爬虫示例...")
    await crawlee_news_example()
    
    # 示例3: 完整流水线
    print("\n[3/4] 完整数据流水线示例...")
    
    config = PipelineConfig(
        raw_data_dir=Path("./data/raw"),
        parsed_data_dir=Path("./data/parsed"),
        output_dir=Path("./data/output"),
    )
    
    pipeline = QuantDataPipeline(config)
    
    # 采集新闻
    print("   采集财经新闻...")
    news = await pipeline.collect_news(["宁德时代", "新能源"])
    print(f"   采集到 {len(news)} 条新闻")
    
    # 解析研报（如果有的话）
    print("   解析研报...")
    pdf_files = list(config.raw_data_dir.glob("*.pdf"))
    if pdf_files:
        for pdf in pdf_files[:3]:  # 最多处理3个
            content = pipeline.parse_report(pdf)
            if content:
                metrics = pipeline.extract_metrics(content)
                pipeline.save_result({
                    "file": str(pdf),
                    "metrics": metrics,
                }, f"{pdf.stem}_analysis.json")
    else:
        print("   未找到研报文件，跳过解析步骤")
        print("   (请将PDF文件放入 ./data/raw/ 目录)")
    
    # 示例4: 研报分析
    print("\n[4/4] 研报分析示例...")
    sample_content = {
        "title": "某公司深度研究报告",
        "text": "我们看好公司未来发展，目标价150元，给予买入评级...",
        "tables": [{"title": "利润表", "data": []}],
        "images": [],
    }
    analysis = analyze_with_skill(sample_content)
    print(analysis)
    
    print("\n" + "=" * 60)
    print("示例演示完成!")
    print("=" * 60)
    print("\n下一步:")
    print("1. pip install mineru crawlee")
    print("2. 将PDF文件放入 ./data/raw/ 目录")
    print("3. 修改示例代码中的选择器以适配目标网站")
    print("4. 运行完整流水线: python examples.py")


if __name__ == "__main__":
    asyncio.run(main())
