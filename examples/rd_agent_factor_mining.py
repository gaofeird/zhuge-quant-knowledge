#!/usr/bin/env python3
"""
RD-Agent 自动化因子挖掘示例
基于微软 Qlib 生态的 LLM驱动自主进化Agent

核心特性：
1. Co-STEER 代码生成框架
2. 自动化因子挖掘流程
3. SOTA 性能 (Alphaflat数据集)
"""

import os
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import numpy as np
import pandas as pd


class FactorCategory(Enum):
    """因子类别"""
    PRICE = "price"           # 价格因子
    VOLUME = "volume"         # 量价因子
    MOMENTUM = "momentum"     # 动量因子
    VOLATILITY = "volatility" # 波动率因子
    SENTIMENT = "sentiment"    # 情绪因子


@dataclass
class FactorInfo:
    """因子信息"""
    name: str
    category: FactorCategory
    expression: str
    description: str
    ic: float = 0.0           # 信息系数
    ir: float = 0.0           # 信息比率
    creation_time: datetime = field(default_factory=datetime.now)


@dataclass
class BacktestResult:
    """回测结果"""
    factor_name: str
    strategy_return: float
    benchmark_return: float
    excess_return: float
    max_drawdown: float
    sharpe_ratio: float


class FactorGenerator:
    """因子生成器 (模拟Co-STEER框架)"""
    
    def __init__(self, llm_model: str = "gpt-4o"):
        self.llm_model = llm_model
        self.generated_factors: List[FactorInfo] = []
    
    def generate_factor(
        self, 
        description: str, 
        category: FactorCategory
    ) -> FactorInfo:
        """
        使用自然语言描述生成因子
        
        Args:
            description: 因子描述 (如 "5日收盘价均线与20日均线的差值")
            category: 因子类别
        """
        # 模拟 LLM 生成因子表达式
        expression_map = {
            "5日收盘价均线与20日均线的差值": "(MA(Close,5) - MA(Close,20)) / MA(Close,20)",
            "成交量加权价格": "WVAP = Sum(Close * Volume, 20) / Sum(Volume, 20)",
            "价格波动率": "STD(Close, 20) / MA(Close, 20)",
            "动量因子": "(Close - Close(20)) / Close(20)",
        }
        
        expression = expression_map.get(description, f"CustomFactor({description})")
        
        factor = FactorInfo(
            name=f"{category.value}_{len(self.generated_factors)+1}",
            category=category,
            expression=expression,
            description=description,
            ic=np.random.uniform(0.02, 0.08),
            ir=np.random.uniform(0.3, 1.2),
        )
        
        self.generated_factors.append(factor)
        return factor
    
    def batch_generate(
        self, 
        descriptions: List[str], 
        categories: List[FactorCategory]
    ) -> List[FactorInfo]:
        """批量生成因子"""
        factors = []
        for desc, cat in zip(descriptions, categories):
            factor = self.generate_factor(desc, cat)
            factors.append(factor)
        return factors


class FactorEvaluator:
    """因子评估器"""
    
    def __init__(self):
        self.evaluation_cache: Dict[str, Dict] = {}
    
    def evaluate(self, factor: FactorInfo, data: pd.DataFrame) -> Dict[str, float]:
        """
        评估因子质量
        
        Metrics:
        - IC (Information Coefficient): 预测能力
        - IR (Information Ratio): 稳定性
        - Rank IC: 排序相关性
        """
        # 模拟评估
        n_samples = len(data) if len(data) > 0 else 252
        
        ic = factor.ic + np.random.uniform(-0.01, 0.01)
        ir = factor.ir + np.random.uniform(-0.1, 0.1)
        rank_ic = ic * np.random.uniform(0.8, 1.0)
        
        evaluation = {
            "IC": ic,
            "IC_t_stat": ic * np.sqrt(n_samples) / 0.03,
            "IC_p_value": max(0.001, 0.05 - ic * 0.5),
            "IR": ir,
            "Rank_IC": rank_ic,
            "Turnover": np.random.uniform(0.05, 0.25),
        }
        
        self.evaluation_cache[factor.name] = evaluation
        return evaluation
    
    def select_top_k(
        self, 
        factors: List[FactorInfo], 
        k: int = 10,
        metric: str = "IC"
    ) -> List[FactorInfo]:
        """选择Top-K因子"""
        scored_factors = []
        for f in factors:
            eval_result = self.evaluation_cache.get(f.name, {})
            score = eval_result.get(metric, 0)
            scored_factors.append((f, score))
        
        scored_factors.sort(key=lambda x: x[1], reverse=True)
        return [f for f, _ in scored_factors[:k]]


class MarketImpactModel:
    """
    交易成本模型
    
    支持模型:
    1. Almgren-Chriss (AC)
    2. Obizhaeva-Wang (OW)
    3. SqrtImpact (平方根法则)
    """
    
    @staticmethod
    def almgren_chriss(
        num_shares: float,
        volatility: float,
        participation_rate: float = 0.1,
        risk_aversion: float = 1e-6
    ) -> Dict[str, float]:
        """
        Almgren-Chriss 最优执行模型
        
        Args:
            num_shares: 交易数量
            volatility: 波动率
            participation_rate: 参与率
            risk_aversion: 风险厌恶系数
        """
        # 最优交易速度
        kappa = np.sqrt(risk_aversion * volatility ** 2)
        
        # 预期市场冲击
        permanent_impact = 0.1 * participation_rate
        temporary_impact = 0.1 * np.sqrt(participation_rate)
        
        # 总交易成本
        total_cost = (
            permanent_impact * num_shares +
            temporary_impact * np.sqrt(num_shares)
        )
        
        return {
            "optimal_speed": kappa,
            "permanent_impact": permanent_impact,
            "temporary_impact": temporary_impact,
            "total_cost": total_cost,
            "execution_time": 1 / kappa if kappa > 0 else float('inf'),
        }
    
    @staticmethod
    def sqrt_impact(
        num_shares: float,
        daily_volume: float,
        volatility: float,
        alpha: float = 0.5
    ) -> Dict[str, float]:
        """
        平方根市场冲击模型
        
        Formula: Impact = alpha * sigma * sqrt(Q/V)
        """
        participation = num_shares / daily_volume if daily_volume > 0 else 1.0
        
        impact = alpha * volatility * np.sqrt(participation)
        cost = impact * num_shares
        
        return {
            "participation_rate": participation,
            "impact_per_share": impact,
            "total_market_impact": cost,
            "cost_bps": (cost / (num_shares * volatility)) * 10000 if num_shares > 0 else 0,
        }
    
    @staticmethod
    def obizhaeva_wang(
        num_shares: float,
        daily_volume: float,
        volatility: float,
        liquidation_time: float = 1.0,
       eta: float = 0.1
    ) -> Dict[str, float]:
        """
        Obizhaeva-Wang 流动性冲击模型
        
        考虑价格回复效应
        """
        # 永久冲击
        permanent_impact = eta * (num_shares / daily_volume) * volatility
        
        # 临时冲击
        temp_impact = eta * np.sqrt(num_shares / daily_volume) * volatility
        
        # 总冲击
        total_impact = permanent_impact + temp_impact
        
        return {
            "permanent_impact": permanent_impact,
            "temporary_impact": temp_impact,
            "total_impact": total_impact,
            "avg_spread_cost": eta * volatility / np.sqrt(liquidation_time),
        }


class FactorBacktester:
    """因子回测引擎"""
    
    def __init__(self, initial_capital: float = 1000000):
        self.initial_capital = initial_capital
        self.results: List[BacktestResult] = []
    
    def backtest(
        self, 
        factor: FactorInfo,
        price_data: pd.DataFrame,
        holding_period: int = 5
    ) -> BacktestResult:
        """
        因子回测
        
        策略:
        1. 因子值 top 20% -> 做多
        2. 因子值 bottom 20% -> 做空
        3. 等权持仓
        """
        n = len(price_data)
        if n < holding_period + 20:
            return BacktestResult(
                factor_name=factor.name,
                strategy_return=0.0,
                benchmark_return=0.0,
                excess_return=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0
            )
        
        # 模拟收益率
        returns = np.random.normal(0.0005, 0.02, n)  # 日收益率
        
        # 因子选股收益
        factor_return = returns + factor.ic * np.random.randn(n) * 0.1
        
        # 策略收益
        strategy_returns = factor_return[holding_period:] - factor_return[:-holding_period]
        benchmark_returns = returns[holding_period:]
        
        # 计算指标
        cumulative_strategy = np.cumprod(1 + strategy_returns)
        cumulative_benchmark = np.cumprod(1 + benchmark_returns)
        
        strategy_total = cumulative_strategy[-1] - 1
        benchmark_total = cumulative_benchmark[-1] - 1
        excess_return = strategy_total - benchmark_total
        
        # 最大回撤
        peak = np.maximum.accumulate(cumulative_strategy)
        drawdown = (cumulative_strategy - peak) / peak
        max_drawdown = abs(drawdown.min())
        
        # 夏普比率
        sharpe = np.mean(strategy_returns) / np.std(strategy_returns) * np.sqrt(252) if np.std(strategy_returns) > 0 else 0
        
        result = BacktestResult(
            factor_name=factor.name,
            strategy_return=strategy_total,
            benchmark_return=benchmark_total,
            excess_return=excess_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe
        )
        
        self.results.append(result)
        return result


class RDAgentWorkflow:
    """
    RD-Agent 完整工作流
    
    模拟 LLM驱动的自主进化Agent流程:
    1. 需求理解 (因子描述)
    2. 代码生成 (Co-STEER)
    3. 因子评估
    4. 策略回测
    5. 优化迭代
    """
    
    def __init__(self):
        self.generator = FactorGenerator()
        self.evaluator = FactorEvaluator()
        self.backtester = FactorBacktester()
        self.best_factors: List[FactorInfo] = []
    
    def run_workflow(
        self,
        requirements: List[str],
        categories: List[FactorCategory],
        market_data: pd.DataFrame,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        执行完整工作流
        
        Returns:
            workflow_result: {
                "generated_factors": [...],
                "top_factors": [...],
                "backtest_results": [...],
                "summary": {...}
            }
        """
        print("\n" + "="*60)
        print("  RD-Agent 自动化因子挖掘工作流")
        print("="*60)
        
        # Step 1: 生成因子
        print("\n[Step 1/4] 生成因子...")
        factors = self.generator.batch_generate(requirements, categories)
        print(f"  成功生成 {len(factors)} 个因子")
        
        # Step 2: 评估因子
        print("\n[Step 2/4] 评估因子...")
        for factor in factors:
            eval_result = self.evaluator.evaluate(factor, market_data)
            print(f"  {factor.name}: IC={eval_result['IC']:.4f}, IR={eval_result['IR']:.4f}")
        
        # Step 3: 选择Top-K
        print(f"\n[Step 3/4] 选择 Top-{top_k} 因子...")
        top_factors = self.evaluator.select_top_k(factors, k=top_k, metric="IC")
        print(f"  选中: {[f.name for f in top_factors]}")
        
        # Step 4: 回测
        print("\n[Step 4/4] 回测验证...")
        backtest_results = []
        for factor in top_factors:
            result = self.backtester.backtest(factor, market_data)
            backtest_results.append(result)
            print(f"  {factor.name}: 收益={result.strategy_return:.2%}, 夏普={result.sharpe_ratio:.2f}")
        
        # 汇总
        summary = {
            "total_generated": len(factors),
            "top_k": top_k,
            "avg_ic": np.mean([r['IC'] for f in factors for k, r in [(f.name, self.evaluator.evaluation_cache[f.name])] ]),
            "best_factor": top_factors[0].name if top_factors else None,
            "best_sharpe": max((r.sharpe_ratio for r in backtest_results), default=0),
        }
        
        return {
            "generated_factors": factors,
            "top_factors": top_factors,
            "backtest_results": backtest_results,
            "summary": summary,
        }


def demo():
    """演示 RD-Agent 工作流"""
    
    print("\n" + "="*70)
    print("  RD-Agent 自动化因子挖掘框架演示")
    print("="*70)
    
    # 准备模拟市场数据
    dates = pd.date_range("2025-01-01", "2026-04-01", freq="B")
    n = len(dates)
    market_data = pd.DataFrame({
        "date": dates,
        "open": np.random.uniform(30, 35, n),
        "high": np.random.uniform(32, 38, n),
        "low": np.random.uniform(28, 32, n),
        "close": np.random.uniform(30, 35, n),
        "volume": np.random.uniform(1e6, 5e6, n),
    })
    
    # 定义需求
    requirements = [
        "5日收盘价均线与20日均线的差值",
        "成交量加权价格",
        "价格波动率",
        "动量因子",
        "MACD金叉信号",
        "布林带突破",
    ]
    categories = [
        FactorCategory.MOMENTUM,
        FactorCategory.VOLUME,
        FactorCategory.VOLATILITY,
        FactorCategory.MOMENTUM,
        FactorCategory.TECHNICAL,
        FactorCategory.TECHNICAL,
    ]
    
    # 运行工作流
    agent = RDAgentWorkflow()
    result = agent.run_workflow(requirements, categories, market_data, top_k=3)
    
    # 打印汇总
    print("\n" + "="*60)
    print("  工作流执行汇总")
    print("="*60)
    print(f"\n生成因子总数: {result['summary']['total_generated']}")
    print(f"选中因子数量: {result['summary']['top_k']}")
    print(f"最优因子: {result['summary']['best_factor']}")
    print(f"最优夏普比率: {result['summary']['best_sharpe']:.2f}")
    
    # 市场冲击测试
    print("\n" + "="*60)
    print("  市场冲击模型测试")
    print("="*60)
    
    mi_model = MarketImpactModel()
    
    # 测试用例
    test_trades = [
        {"shares": 10000, "daily_vol": 500000, "vol": 0.02},
        {"shares": 50000, "daily_vol": 500000, "vol": 0.02},
        {"shares": 100000, "daily_vol": 500000, "vol": 0.02},
    ]
    
    print("\n不同交易规模的市场冲击:")
    print("-" * 60)
    for trade in test_trades:
        result = mi_model.sqrt_impact(
            trade["shares"],
            trade["daily_vol"],
            trade["vol"]
        )
        print(f"  交易量 {trade['shares']:,}: 冲击={result['impact_per_share']:.4f}, "
              f"总成本={result['total_market_impact']:.4f}, "
              f"成本基点={result['cost_bps']:.2f}bps")


if __name__ == "__main__":
    demo()
