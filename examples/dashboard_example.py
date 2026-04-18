"""
daily_stock_analysis 决策仪表盘设计示例

参考: https://github.com/wanrenhuifu/daily_stock_analysis

核心设计思路:
1. 颜色编码信号: 🟢买入 🟡观望 🔴卖出
2. 精确买卖点位: 狙击价/止损价/目标价
3. 操作检查清单: ✅⚠️❌
4. 一句话结论
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Signal(Enum):
    """交易信号枚举"""
    BUY = "🟢买入"      # 积极买入信号
    HOLD = "🟡观望"     # 中性信号
    SELL = "🔴卖出"     # 卖出信号
    DANGER = "⚠️危险"   # 风险警告


@dataclass
class ChecklistItem:
    """检查清单项"""
    item: str          # 检查项名称
    passed: bool        # 是否通过
    warning: bool = False  # 是否警告


@dataclass
class TradingLevels:
    """交易关键点位"""
    entry: float        # 狙击买入价
    stop_loss: float    # 止损价
    target: float       # 目标价
    
    @property
    def risk_ratio(self) -> float:
        """风险收益比"""
        risk = self.entry - self.stop_loss
        reward = self.target - self.entry
        return reward / risk if risk > 0 else 0
    
    @property
    def stop_loss_pct(self) -> float:
        """止损百分比"""
        return (self.entry - self.stop_loss) / self.entry * 100


@dataclass
class StockDecision:
    """个股决策仪表盘"""
    stock_code: str
    stock_name: str
    signal: Signal
    confidence: float          # 信心度 0-1
    conclusion: str            # 一句话结论
    levels: TradingLevels      # 关键点位
    checklist: List[ChecklistItem]
    deviation_ratio: float     # 乖离率
    ma_status: str           # 均线状态描述
    
    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        signal_emoji = self.signal.value
        
        lines = [
            f"{signal_emoji} {self.signal.name} | {self.stock_name}({self.stock_code})",
            f"📌 {self.conclusion}",
            f"💰 狙击: 买入{self.levels.entry:.2f} | 止损{self.levels.stop_loss:.2f} | 目标{self.levels.target:.2f}",
            f"   (止损{self.levels.stop_loss_pct:.1f}% | 风险收益比{self.levels.risk_ratio:.2f})",
        ]
        
        # 添加检查清单
        checklist_str = "".join(
            "✅" if item.passed else ("⚠️" if item.warning else "❌")
            for item in self.checklist
        )
        checklist_desc = " ".join(
            f"{'✅' if item.passed else ('⚠️' if item.warning else '❌')}{item.item}"
            for item in self.checklist
        )
        lines.append(checklist_desc)
        
        return "\n".join(lines)


@dataclass
class DashboardSummary:
    """仪表盘汇总"""
    date: str
    total_count: int
    buy_count: int
    hold_count: int
    sell_count: int
    decisions: List[StockDecision]
    
    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        lines = [
            f"📊 {self.date} 决策仪表盘",
            f"{self.total_count}只股票 | 🟢买入:{self.buy_count} 🟡观望:{self.hold_count} 🔴卖出:{self.sell_count}",
            "",
            "---",
        ]
        
        # 按信号分类排序
        sorted_decisions = sorted(
            self.decisions,
            key=lambda x: [Signal.BUY, Signal.HOLD, Signal.SELL, Signal.DANGER].index(x.signal)
        )
        
        for decision in sorted_decisions:
            lines.append(decision.to_markdown())
            lines.append("")
        
        return "\n".join(lines)


def analyze_stock_deviation(
    current_price: float,
    ma5: float,
    ma10: float,
    ma20: float
) -> tuple[Signal, str, float]:
    """
    基于乖离率和均线判断交易信号
    
    Args:
        current_price: 当前价格
        ma5, ma10, ma20: 均线价格
    
    Returns:
        (signal, conclusion, deviation_ratio)
    """
    deviation_ratio = (current_price - ma5) / ma5 * 100
    
    # 判断条件
    ma_aligned = ma5 > ma10 > ma20  # 多头排列
    near_ma5 = abs(deviation_ratio) < 2  # 接近MA5
    deviation_safe = abs(deviation_ratio) < 5  # 乖离率安全
    
    # 生成结论
    if not deviation_safe:
        signal = Signal.DANGER
        conclusion = f"乖离率{deviation_ratio:.1f}%超过5%警戒线，严禁追高"
    elif deviation_ratio < -2:
        if ma_aligned:
            signal = Signal.BUY
            conclusion = f"缩量回踩MA5支撑，乖离率{deviation_ratio:.1f}%处于最佳买点"
        else:
            signal = Signal.HOLD
            conclusion = f"偏离MA5{deviation_ratio:.1f}%，均线尚未多头，等待确认"
    elif deviation_ratio > 5:
        signal = Signal.SELL
        conclusion = f"乖离率{deviation_ratio:.1f}%过高，注意回调风险"
    elif ma_aligned and near_ma5:
        signal = Signal.BUY
        conclusion = f"均线多头排列良好，乖离率{deviation_ratio:.1f}%安全区间"
    else:
        signal = Signal.HOLD
        conclusion = f"当前乖离率{deviation_ratio:.1f}%，趋势不明朗"
    
    return signal, conclusion, deviation_ratio


def generate_trading_levels(
    current_price: float,
    ma5: float,
    signal: Signal
) -> TradingLevels:
    """生成交易关键点位"""
    # 基于信号类型计算点位
    if signal == Signal.BUY:
        # 买入信号：以当前价或略低于MA5作为狙击价
        entry = current_price
        stop_loss = ma5 * 0.98  # 略低于MA5
        target = current_price * 1.08  # 8%目标
    elif signal == Signal.HOLD:
        # 观望：设置当前价附近
        entry = current_price
        stop_loss = current_price * 0.97
        target = current_price * 1.05
    else:
        # 卖出/危险：反转点位
        entry = current_price * 0.98
        stop_loss = current_price
        target = current_price * 0.95
    
    return TradingLevels(entry=entry, stop_loss=stop_loss, target=target)


def generate_checklist(
    ma5: float,
    ma10: float,
    ma20: float,
    volume_ratio: float,
    deviation_ratio: float
) -> List[ChecklistItem]:
    """生成操作检查清单"""
    checklist = []
    
    # 均线多头排列
    ma_aligned = ma5 > ma10 > ma20
    checklist.append(ChecklistItem("多头排列", ma_aligned))
    
    # 乖离安全
    deviation_safe = abs(deviation_ratio) < 5
    checklist.append(ChecklistItem(
        "乖离安全", 
        deviation_safe,
        warning=(abs(deviation_ratio) > 3 and abs(deviation_ratio) < 5)
    ))
    
    # 量能配合
    volume_ok = volume_ratio > 0.8
    checklist.append(ChecklistItem(
        "量能配合",
        volume_ok,
        warning=(0.5 < volume_ratio <= 0.8)
    ))
    
    # 趋势确认
    trend_ok = ma5 > ma20
    checklist.append(ChecklistItem("趋势向上", trend_ok))
    
    return checklist


# 示例使用
if __name__ == "__main__":
    # 模拟贵州茅台分析
    stock_code = "600519"
    stock_name = "贵州茅台"
    current_price = 1780.0
    ma5 = 1760.0
    ma10 = 1740.0
    ma20 = 1720.0
    volume_ratio = 0.75  # 量能萎缩
    
    # 分析
    signal, conclusion, deviation = analyze_stock_deviation(
        current_price, ma5, ma10, ma20
    )
    
    # 生成点位
    levels = generate_trading_levels(current_price, ma5, signal)
    
    # 生成检查清单
    checklist = generate_checklist(ma5, ma10, ma20, volume_ratio, deviation)
    
    # 构建决策
    decision = StockDecision(
        stock_code=stock_code,
        stock_name=stock_name,
        signal=signal,
        confidence=0.85,
        conclusion=conclusion,
        levels=levels,
        checklist=checklist,
        deviation_ratio=deviation,
        ma_status="MA5>MA10>MA20 多头排列"
    )
    
    # 输出仪表盘
    dashboard = DashboardSummary(
        date="2026-04-13",
        total_count=1,
        buy_count=1 if signal == Signal.BUY else 0,
        hold_count=1 if signal == Signal.HOLD else 0,
        sell_count=1 if signal == Signal.SELL else 0,
        decisions=[decision]
    )
    
    print(dashboard.to_markdown())
