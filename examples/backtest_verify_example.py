"""
AI回测验证系统示例

参考: daily_stock_analysis 的回测验证功能

核心功能:
1. 历史分析准确率评估
2. 方向胜率统计
3. 止盈止损命中率
4. 1日next-session验证
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from enum import Enum
import pandas as pd


class PredictionDirection(Enum):
    """预测方向"""
    UP = "UP"      # 预测上涨
    DOWN = "DOWN"  # 预测下跌
    NEUTRAL = "NEUTRAL"  # 预测横盘


@dataclass
class AnalysisRecord:
    """历史分析记录"""
    stock_code: str
    analysis_date: datetime
    predicted_direction: PredictionDirection
    predicted_move: float      # 预测涨跌幅 %
    entry_price: float        # 建议买入价
    stop_loss: float          # 止损价
    target_price: float       # 目标价
    signal: str               # BUY/HOLD/SELL
    confidence: float          # 信心度 0-1


@dataclass
class NextSessionResult:
    """下一交易日验证结果"""
    actual_open: float        # 次日开盘价
    actual_close: float       # 次日收盘价
    actual_high: float        # 次日最高价
    actual_low: float         # 次日最低价
    actual_move: float        # 实际涨跌幅 %
    direction_correct: bool    # 方向判断正确
    stopped_out: bool         # 是否止损
    target_hit: bool          # 是否达到目标
    
    @property
    def result_type(self) -> str:
        """结果分类"""
        if self.stopped_out:
            return "止损"
        if self.target_hit:
            return "止盈"
        if self.direction_correct:
            return "正确"
        return "错误"


@dataclass
class BacktestStatistics:
    """回测统计结果"""
    total_count: int
    direction_wins: int       # 方向正确次数
    direction_win_rate: float  # 方向胜率
    avg_predicted_move: float
    avg_actual_move: float
    
    stop_loss_count: int      # 止损次数
    stop_loss_rate: float     # 止损率
    
    target_hit_count: int     # 达标次数
    target_hit_rate: float    # 达标率
    
    # 按信号分类统计
    signal_stats: Dict[str, Dict] = field(default_factory=dict)
    
    def to_summary(self) -> str:
        """生成统计摘要"""
        return f"""
=== 回测统计汇总 ===

总分析次数: {self.total_count}
方向胜率: {self.direction_win_rate:.1%}
预测平均涨幅: {self.avg_predicted_move:.2f}%
实际平均涨幅: {self.avg_actual_move:.2f}%

止损统计:
  - 止损次数: {self.stop_loss_count}
  - 止损率: {self.stop_loss_rate:.1%}

达标统计:
  - 达标次数: {self.target_hit_count}
  - 达标率: {self.target_hit_rate:.1%}

按信号统计:
""" + "\n".join([
            f"  {signal}: 胜率{stats['win_rate']:.1%}, 平均涨幅{stats['avg_move']:.2f}%"
            for signal, stats in self.signal_stats.items()
        ])


class AIBacktestValidator:
    """AI回测验证器"""
    
    def __init__(self):
        self.records: List[AnalysisRecord] = []
        self.results: Dict[str, NextSessionResult] = {}  # key: f"{code}_{date}"
    
    def add_record(self, record: AnalysisRecord):
        """添加分析记录"""
        self.records.append(record)
    
    def add_result(self, stock_code: str, analysis_date: datetime, result: NextSessionResult):
        """添加验证结果"""
        key = f"{stock_code}_{analysis_date.strftime('%Y%m%d')}"
        self.results[key] = result
    
    def validate_record(
        self,
        stock_code: str,
        analysis_date: datetime,
        next_open: float,
        next_close: float,
        next_high: float,
        next_low: float
    ) -> Optional[NextSessionResult]:
        """验证单条记录"""
        # 找到对应的分析记录
        record = self._find_record(stock_code, analysis_date)
        if not record:
            return None
        
        # 计算实际涨跌幅
        actual_move = (next_close - record.entry_price) / record.entry_price * 100
        
        # 判断方向是否正确
        direction_correct = (
            (record.predicted_direction == PredictionDirection.UP and actual_move > 0) or
            (record.predicted_direction == PredictionDirection.DOWN and actual_move < 0) or
            (record.predicted_direction == PredictionDirection.NEUTRAL and abs(actual_move) < 1)
        )
        
        # 判断是否止损
        stopped_out = next_low <= record.stop_loss
        
        # 判断是否达标
        target_hit = next_high >= record.target_price
        
        result = NextSessionResult(
            actual_open=next_open,
            actual_close=next_close,
            actual_high=next_high,
            actual_low=next_low,
            actual_move=actual_move,
            direction_correct=direction_correct,
            stopped_out=stopped_out,
            target_hit=target_hit
        )
        
        # 存储结果
        self.add_result(stock_code, analysis_date, result)
        
        return result
    
    def _find_record(self, stock_code: str, analysis_date: datetime) -> Optional[AnalysisRecord]:
        """查找分析记录"""
        for record in self.records:
            if (record.stock_code == stock_code and 
                record.analysis_date.date() == analysis_date.date()):
                return record
        return None
    
    def get_statistics(
        self,
        stock_code: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> BacktestStatistics:
        """计算统计结果"""
        # 过滤记录
        filtered_records = self.records
        if stock_code:
            filtered_records = [r for r in filtered_records if r.stock_code == stock_code]
        if start_date:
            filtered_records = [r for r in filtered_records if r.analysis_date >= start_date]
        if end_date:
            filtered_records = [r for r in filtered_records if r.analysis_date <= end_date]
        
        # 获取对应的结果
        valid_results = []
        for record in filtered_records:
            key = f"{record.stock_code}_{record.analysis_date.strftime('%Y%m%d')}"
            if key in self.results:
                valid_results.append((record, self.results[key]))
        
        if not valid_results:
            return BacktestStatistics(
                total_count=0,
                direction_wins=0,
                direction_win_rate=0,
                avg_predicted_move=0,
                avg_actual_move=0,
                stop_loss_count=0,
                stop_loss_rate=0,
                target_hit_count=0,
                target_hit_rate=0
            )
        
        total = len(valid_results)
        direction_wins = sum(1 for _, r in valid_results if r.direction_correct)
        stop_loss_count = sum(1 for _, r in valid_results if r.stopped_out)
        target_hit_count = sum(1 for _, r in valid_results if r.target_hit)
        avg_predicted = sum(r.predicted_move for r, _ in valid_results) / total
        avg_actual = sum(r.actual_move for _, r in valid_results) / total
        
        # 按信号分类统计
        signal_stats = {}
        for signal in set(r.signal for r, _ in valid_results):
            signal_records = [(r, res) for r, res in valid_results if r.signal == signal]
            if signal_records:
                signal_total = len(signal_records)
                signal_wins = sum(1 for _, res in signal_records if res.direction_correct)
                signal_avg = sum(res.actual_move for _, res in signal_records) / signal_total
                signal_stats[signal] = {
                    "count": signal_total,
                    "win_rate": signal_wins / signal_total if signal_total > 0 else 0,
                    "avg_move": signal_avg
                }
        
        return BacktestStatistics(
            total_count=total,
            direction_wins=direction_wins,
            direction_win_rate=direction_wins / total if total > 0 else 0,
            avg_predicted_move=avg_predicted,
            avg_actual_move=avg_actual,
            stop_loss_count=stop_loss_count,
            stop_loss_rate=stop_loss_count / total if total > 0 else 0,
            target_hit_count=target_hit_count,
            target_hit_rate=target_hit_count / total if total > 0 else 0,
            signal_stats=signal_stats
        )
    
    def get_validation_view(
        self,
        stock_code: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """获取验证视图DataFrame"""
        # 过滤记录
        filtered_records = self.records
        if stock_code:
            filtered_records = [r for r in filtered_records if r.stock_code == stock_code]
        if start_date:
            filtered_records = [r for r in filtered_records if r.analysis_date >= start_date]
        if end_date:
            filtered_records = [r for r in filtered_records if r.analysis_date <= end_date]
        
        rows = []
        for record in filtered_records:
            key = f"{record.stock_code}_{record.analysis_date.strftime('%Y%m%d')}"
            if key in self.results:
                result = self.results[key]
                rows.append({
                    "股票代码": record.stock_code,
                    "分析日期": record.analysis_date.strftime("%Y-%m-%d"),
                    "信号": record.signal,
                    "AI预测": f"{record.predicted_direction.value} ({record.predicted_move:+.2f}%)",
                    "次日收盘": f"{result.actual_close:.2f}",
                    "实际涨跌幅": f"{result.actual_move:+.2f}%",
                    "验证结果": "✅正确" if result.direction_correct else "❌错误",
                    "止损": "🔴" if result.stopped_out else "-",
                    "达标": "🟢" if result.target_hit else "-"
                })
        
        return pd.DataFrame(rows)


# ==================== 示例使用 ====================

def demo():
    """演示回测验证功能"""
    validator = AIBacktestValidator()
    
    # 模拟历史分析记录
    records_data = [
        ("600519", datetime(2026, 4, 1), PredictionDirection.UP, 2.5, 1750, 1720, 1850, "BUY", 0.85),
        ("600519", datetime(2026, 4, 2), PredictionDirection.UP, 1.8, 1760, 1730, 1860, "BUY", 0.80),
        ("600519", datetime(2026, 4, 3), PredictionDirection.DOWN, -1.5, 1780, 1750, 1790, "SELL", 0.75),
        ("000858", datetime(2026, 4, 1), PredictionDirection.UP, 3.0, 28.5, 28.0, 30.0, "BUY", 0.88),
        ("000858", datetime(2026, 4, 2), PredictionDirection.UP, 2.0, 29.0, 28.5, 31.0, "BUY", 0.82),
    ]
    
    for data in records_data:
        record = AnalysisRecord(
            stock_code=data[0],
            analysis_date=data[1],
            predicted_direction=data[2],
            predicted_move=data[3],
            entry_price=data[4],
            stop_loss=data[5],
            target_price=data[6],
            signal=data[7],
            confidence=data[8]
        )
        validator.add_record(record)
    
    # 模拟验证结果 (次日行情)
    results_data = [
        # (stock_code, date, open, close, high, low)
        ("600519", datetime(2026, 4, 1), 1755, 1780, 1795, 1748),  # 涨1.71%
        ("600519", datetime(2026, 4, 2), 1765, 1775, 1782, 1755),  # 涨0.85%
        ("600519", datetime(2026, 4, 3), 1770, 1760, 1780, 1755),   # 跌1.12%
        ("000858", datetime(2026, 4, 1), 28.8, 29.5, 29.8, 28.6),  # 涨3.51%
        ("000858", datetime(2026, 4, 2), 29.3, 29.0, 29.5, 28.8),  # 跌0.17%
    ]
    
    for data in results_data:
        validator.validate_record(
            stock_code=data[0],
            analysis_date=data[1],
            next_open=data[2],
            next_close=data[3],
            next_high=data[4],
            next_low=data[5]
        )
    
    # 获取统计结果
    stats = validator.get_statistics()
    print(stats.to_summary())
    
    # 获取验证视图
    print("\n=== 验证明细 ===")
    df = validator.get_validation_view()
    print(df.to_string(index=False))


if __name__ == "__main__":
    demo()
