#!/usr/bin/env python3
"""
TradingAgents 多智能体协作框架示例
基于 TauricResearch/TradingAgents v0.2.3

核心特性：
1. 七角色虚拟交易公司架构
2. 多空辩论机制(Dialectical Process)
3. 多LLM提供商支持
4. 五级评分体系
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json


class Signal(Enum):
    """交易信号枚举"""
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    DANGER = "DANGER"


class AnalystType(Enum):
    """分析师类型"""
    FUNDAMENTAL = "fundamental"      # 基本面分析师
    SENTIMENT = "sentiment"          # 情绪分析师
    NEWS = "news"                    # 新闻分析师
    TECHNICAL = "technical"          # 技术分析师


@dataclass
class AnalystOpinion:
    """分析师观点"""
    analyst_type: AnalystType
    stock_code: str
    analysis: str
    confidence: float  # 0.0-1.0
    evidence: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DebateResult:
    """辩论结果"""
    bull_point: str      # 看涨论点
    bear_point: str      # 看跌论点
    final_verdict: Signal
    confidence: float
    reasoning_chain: List[str] = field(default_factory=list)


class BaseAnalyst:
    """分析师基类"""
    
    def __init__(self, analyst_type: AnalystType, llm_provider: str = "openai"):
        self.analyst_type = analyst_type
        self.llm_provider = llm_provider
        self.name = f"{analyst_type.value}_analyst"
    
    def analyze(self, stock_code: str, market_data: Dict[str, Any]) -> AnalystOpinion:
        """执行分析"""
        raise NotImplementedError
    
    def _build_prompt(self, stock_code: str, data: Dict) -> str:
        """构建分析提示词"""
        return f"Analyze {stock_code} from {self.analyst_type.value} perspective"


class FundamentalAnalyst(BaseAnalyst):
    """基本面分析师"""
    
    def __init__(self, llm_provider: str = "openai"):
        super().__init__(AnalystType.FUNDAMENTAL, llm_provider)
    
    def analyze(self, stock_code: str, market_data: Dict[str, Any]) -> AnalystOpinion:
        """基本面分析"""
        # 模拟基本面分析逻辑
        financials = market_data.get("financials", {})
        
        analysis = f"""
        {stock_code} 基本面分析报告
        ==========================
        
        1. 盈利能力分析
        - ROE: {financials.get('roe', 'N/A')}%
        - 毛利率: {financials.get('gross_margin', 'N/A')}%
        - 净利率: {financials.get('net_margin', 'N/A')}%
        
        2. 财务健康
        - 负债率: {financials.get('debt_ratio', 'N/A')}%
        - 流动比率: {financials.get('current_ratio', 'N/A')}
        
        3. 估值水平
        - PE: {financials.get('pe', 'N/A')}
        - PB: {financials.get('pb', 'N/A')}
        
        综合评估：基于财务数据，建议{'买入' if financials.get('roe', 0) > 15 else '观望'}
        """
        
        return AnalystOpinion(
            analyst_type=self.analyst_type,
            stock_code=stock_code,
            analysis=analysis,
            confidence=0.75,
            evidence=[
                f"ROE {financials.get('roe', 0)}%",
                f"PE {financials.get('pe', 0)}"
            ]
        )


class SentimentAnalyst(BaseAnalyst):
    """情绪分析师"""
    
    def __init__(self, llm_provider: str = "openai"):
        super().__init__(AnalystType.SENTIMENT, llm_provider)
    
    def analyze(self, stock_code: str, market_data: Dict[str, Any]) -> AnalystOpinion:
        """情绪分析"""
        sentiment_data = market_data.get("sentiment", {})
        
        analysis = f"""
        {stock_code} 市场情绪报告
        ========================
        
        1. 机构评级
        - 买入: {sentiment_data.get('buy_rating', 0)}家
        - 持有: {sentiment_data.get('hold_rating', 0)}家
        - 卖出: {sentiment_data.get('sell_rating', 0)}家
        
        2. 资金流向
        - 主力净流入: {sentiment_data.get('main_net_flow', 0)}万
        - 北向资金: {sentiment_data.get('north_flow', 0)}万
        
        3. 情绪指数: {sentiment_data.get('sentiment_index', 50)}/100
        
        综合评估：{'积极' if sentiment_data.get('sentiment_index', 50) > 60 else '中性'}
        """
        
        return AnalystOpinion(
            analyst_type=self.analyst_type,
            stock_code=stock_code,
            analysis=analysis,
            confidence=0.70,
            evidence=[f"情绪指数 {sentiment_data.get('sentiment_index', 50)}"]
        )


class NewsAnalyst(BaseAnalyst):
    """新闻分析师"""
    
    def __init__(self, llm_provider: str = "openai"):
        super().__init__(AnalystType.NEWS, llm_provider)
    
    def analyze(self, stock_code: str, market_data: Dict[str, Any]) -> AnalystOpinion:
        """新闻分析"""
        news_data = market_data.get("news", [])
        
        analysis = f"""
        {stock_code} 新闻舆情报告
        ======================
        
        最近新闻 ({len(news_data)}条):
        {chr(10).join([f"- {n.get('title', '')}" for n in news_data[:5]])}
        
        舆情倾向: {'偏多' if market_data.get('news_sentiment', 0) > 0 else '偏空'}
        """
        
        return AnalystOpinion(
            analyst_type=self.analyst_type,
            stock_code=stock_code,
            analysis=analysis,
            confidence=0.65,
            evidence=[f"新闻数量 {len(news_data)}"]
        )


class TechnicalAnalyst(BaseAnalyst):
    """技术分析师"""
    
    def __init__(self, llm_provider: str = "openai"):
        super().__init__(AnalystType.TECHNICAL, llm_provider)
    
    def analyze(self, stock_code: str, market_data: Dict[str, Any]) -> AnalystOpinion:
        """技术分析"""
        tech_data = market_data.get("technical", {})
        
        analysis = f"""
        {stock_code} 技术分析报告
        ======================
        
        1. 趋势指标
        - MA5: {tech_data.get('ma5', 0)}
        - MA20: {tech_data.get('ma20', 0)}
        - MA60: {tech_data.get('ma60', 0)}
        
        2. 动量指标
        - MACD: {tech_data.get('macd', 0)}
        - RSI: {tech_data.get('rsi', 50)}
        
        3. 布林带
        - 上轨: {tech_data.get('boll_upper', 0)}
        - 中轨: {tech_data.get('boll_mid', 0)}
        - 下轨: {tech_data.get('boll_lower', 0)}
        
        综合评估：{'多头趋势' if tech_data.get('ma5', 0) > tech_data.get('ma20', 0) else '空头趋势'}
        """
        
        return AnalystOpinion(
            analyst_type=self.analyst_type,
            stock_code=stock_code,
            analysis=analysis,
            confidence=0.72,
            evidence=[f"MA金叉: {tech_data.get('ma_cross', False)}"]
        )


class BullResearcher:
    """看涨研究员"""
    
    def __init__(self):
        self.name = "bull_researcher"
    
    def generate_bull_case(self, opinions: List[AnalystOpinion]) -> str:
        """生成看涨论点"""
        bullish_evidence = [
            op.evidence[i] for op in opinions 
            if op.confidence > 0.6 for i in range(len(op.evidence))
        ]
        
        return f"""
        【看涨论点】
        基于以下积极因素:
        {chr(10).join([f"  • {e}" for e in bullish_evidence[:5]])}
        
        核心逻辑：
        1. 基本面稳健，盈利能力持续改善
        2. 市场情绪转暖，资金持续流入
        3. 技术面呈现多头排列
        """
    
    def score_opportunity(self, opinions: List[AnalystOpinion]) -> float:
        """评分机会"""
        total_confidence = sum(op.confidence for op in opinions)
        return min(total_confidence / len(opinions) + 0.2, 1.0)


class BearResearcher:
    """看跌研究员"""
    
    def __init__(self):
        self.name = "bear_researcher"
    
    def generate_bear_case(self, opinions: List[AnalystOpinion]) -> str:
        """生成看跌论点"""
        risk_factors = [
            "估值偏高",
            "市场情绪过度乐观",
            "技术面超买"
        ]
        
        return f"""
        【看跌论点】
        关注以下风险因素:
        {chr(10).join([f"  • {r}" for r in risk_factors])}
        
        核心风险：
        1. 估值处于历史高位
        2. 获利盘回吐压力
        3. 宏观环境不确定性
        """
    
    def score_risk(self, opinions: List[AnalystOpinion]) -> float:
        """评估风险"""
        return 0.4  # 模拟风险评分


class DialecticalDebate:
    """多空辩论机制"""
    
    def __init__(self):
        self.bull = BullResearcher()
        self.bear = BearResearcher()
        self.debate_rounds = 2
    
    def conduct_debate(self, opinions: List[AnalystOpinion]) -> DebateResult:
        """执行辩论"""
        # 第一轮：各自陈述
        bull_case = self.bull.generate_bull_case(opinions)
        bear_case = self.bear.generate_bear_case(opinions)
        
        # 综合评估
        bull_score = self.bull.score_opportunity(opinions)
        bear_score = self.bear.score_risk(opinions)
        
        # 最终判决
        net_score = bull_score - bear_score
        
        if net_score > 0.3:
            verdict = Signal.BUY
            confidence = min(bull_score, 0.95)
        elif net_score > 0.1:
            verdict = Signal.HOLD
            confidence = 0.65
        elif net_score > -0.1:
            verdict = Signal.HOLD
            confidence = 0.55
        else:
            verdict = Signal.SELL
            confidence = min(bear_score, 0.90)
        
        return DebateResult(
            bull_point=bull_case,
            bear_point=bear_case,
            final_verdict=verdict,
            confidence=confidence,
            reasoning_chain=[
                f"看涨评分: {bull_score:.2f}",
                f"看跌评分: {bear_score:.2f}",
                f"综合得分: {net_score:.2f}",
                f"最终判决: {verdict.value}"
            ]
        )


class TradingAgentsGraph:
    """
    TradingAgents 多智能体协作图
    
    模拟七角色虚拟交易公司架构:
    1. 分析团队 (4个分析师)
    2. 研究团队 (多空辩论)
    3. 交易决策
    """
    
    def __init__(self, debug: bool = False, config: Optional[Dict] = None):
        self.debug = debug
        self.config = config or {}
        
        # 初始化分析团队
        self.analysts = [
            FundamentalAnalyst(),
            SentimentAnalyst(),
            NewsAnalyst(),
            TechnicalAnalyst(),
        ]
        
        # 初始化辩论机制
        self.debate = DialecticalDebate()
        
        # 记忆系统
        self.memory: List[Dict] = []
    
    def _collect_market_data(self, stock_code: str, date: str) -> Dict[str, Any]:
        """收集市场数据"""
        # 模拟数据，实际应该调用API获取
        return {
            "financials": {
                "roe": 18.5,
                "gross_margin": 45.2,
                "net_margin": 15.3,
                "debt_ratio": 55.0,
                "current_ratio": 1.8,
                "pe": 22.5,
                "pb": 3.2,
            },
            "sentiment": {
                "buy_rating": 25,
                "hold_rating": 12,
                "sell_rating": 3,
                "main_net_flow": 5200,
                "north_flow": 1800,
                "sentiment_index": 68,
            },
            "news": [
                {"title": "公司发布超预期财报", "date": "2026-04-10"},
                {"title": "获得重大订单合同", "date": "2026-04-08"},
            ],
            "technical": {
                "ma5": 35.2,
                "ma20": 34.8,
                "ma60": 33.5,
                "macd": 0.85,
                "rsi": 62,
                "boll_upper": 38.5,
                "boll_mid": 35.0,
                "boll_lower": 31.5,
                "ma_cross": True,
            }
        }
    
    def propagate(self, stock_code: str, date: str = None) -> tuple[str, Dict]:
        """
        执行多智能体协作流程
        
        Returns:
            (decision_type, decision_data)
        """
        date = date or datetime.now().strftime("%Y-%m-%d")
        
        if self.debug:
            print(f"\n{'='*60}")
            print(f"TradingAgents 分析开始: {stock_code} @ {date}")
            print(f"{'='*60}\n")
        
        # Step 1: 收集市场数据
        market_data = self._collect_market_data(stock_code, date)
        
        # Step 2: 分析团队并行分析
        opinions = []
        for analyst in self.analysts:
            if self.debug:
                print(f"  [分析中] {analyst.name}...")
            opinion = analyst.analyze(stock_code, market_data)
            opinions.append(opinion)
            if self.debug:
                print(f"  [完成] {analyst.name} - 置信度: {opinion.confidence:.2f}")
        
        # Step 3: 多空辩论
        if self.debug:
            print(f"\n  [辩论] 多空双方开始辩论...")
        debate_result = self.debate.conduct_debate(opinions)
        
        # Step 4: 记录到记忆
        record = {
            "stock_code": stock_code,
            "date": date,
            "verdict": debate_result.final_verdict.value,
            "confidence": debate_result.confidence,
            "opinions": [
                {"type": op.analyst_type.value, "confidence": op.confidence}
                for op in opinions
            ]
        }
        self.memory.append(record)
        
        # 构建决策输出
        decision = {
            "signal": debate_result.final_verdict,
            "confidence": debate_result.confidence,
            "bull_case": debate_result.bull_point,
            "bear_case": debate_result.bear_point,
            "reasoning_chain": debate_result.reasoning_chain,
            "analyst_summary": {
                "fundamental": opinions[0].analysis,
                "sentiment": opinions[1].analysis,
                "news": opinions[2].analysis,
                "technical": opinions[3].analysis,
            }
        }
        
        if self.debug:
            print(f"\n{'='*60}")
            print(f"最终决策: {decision['signal'].value}")
            print(f"置信度: {decision['confidence']:.2%}")
            print(f"{'='*60}\n")
        
        return "decision", decision
    
    def get_memory(self, stock_code: Optional[str] = None) -> List[Dict]:
        """获取历史决策记忆"""
        if stock_code:
            return [m for m in self.memory if m["stock_code"] == stock_code]
        return self.memory


def demo():
    """演示 TradingAgents 多智能体协作"""
    
    print("\n" + "="*70)
    print("  TradingAgents 多智能体协作框架演示")
    print("="*70 + "\n")
    
    # 初始化
    config = {
        "llm_provider": "openai",
        "model": "gpt-4o",
    }
    ta = TradingAgentsGraph(debug=True, config=config)
    
    # 分析股票
    print("分析标的: 宁德时代 (sz300750)")
    print("-" * 50)
    
    _, decision = ta.propagate("sz300750", "2026-04-13")
    
    # 输出结果
    print("\n" + "="*70)
    print("  分析报告摘要")
    print("="*70)
    print(f"\n【交易信号】{decision['signal'].value}")
    print(f"【置信度】{decision['confidence']:.2%}")
    
    print("\n【推理链】")
    for i, step in enumerate(decision['reasoning_chain'], 1):
        print(f"  {i}. {step}")
    
    print("\n【多空辩论】")
    print(decision['bull_case'])
    print(decision['bear_case'])
    
    return decision


if __name__ == "__main__":
    demo()
