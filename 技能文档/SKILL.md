# 风险管理技能学习笔记

## 一、概述

### 1.1 量化交易中的风险
```
量化交易风险分类
├── 市场风险
│   ├── 系统性风险（大盘下跌）
│   ├── 行业风险（行业政策变化）
│   └── 个股风险（个股暴雷）
│
├── 模型风险
│   ├── 过拟合风险
│   ├── 参数不稳定
│   └── 模型失效
│
├── 执行风险
│   ├── 滑点风险
│   ├── 流动性风险
│   └── 延迟风险
│
└── 操作风险
    ├── 程序错误
    ├── 数据错误
    └── 人为错误
```

### 1.2 风险管理目标
- 控制最大回撤在可接受范围内（通常<20%）
- 提高夏普比率（通常>1.5）
- 平衡风险与收益
- 确保策略长期稳定盈利

---

## 二、仓位管理

### 2.1 固定比例仓位
```python
class FixedPositionManager:
    def __init__(self, position_ratio=0.1):
        """
        固定比例仓位管理
        position_ratio: 每次买入使用的资金比例（如0.1表示10%）
        """
        self.position_ratio = position_ratio

    def calculate_position_size(self, account_value, price):
        """
        计算买入数量
        """
        # 可用资金
        available_cash = account_value * self.position_ratio

        # 计算可买入数量
        position_size = int(available_cash / price)

        return position_size

# 使用示例
manager = FixedPositionManager(position_ratio=0.1)
account_value = 1000000  # 100万
price = 100.0

position_size = manager.calculate_position_size(account_value, price)
print(f"买入数量: {position_size}股")
print(f"使用资金: {position_size * price:,.2f}元")
```

### 2.2 凯利公式仓位
```python
class KellyPositionManager:
    def __init__(self):
        """
        凯利公式仓位管理
        """
        pass

    def calculate_kelly_fraction(self, win_rate, avg_win, avg_loss):
        """
        计算凯利比例

        公式: f* = (bp - q) / b

        f* = 最优仓位比例
        b = 赔率 = avg_win / avg_loss
        p = 胜率
        q = 败率 = 1 - p
        """
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - p

        kelly_fraction = (b * p - q) / b

        # 限制在0-1之间
        kelly_fraction = max(0, min(1, kelly_fraction))

        return kelly_fraction

    def calculate_position_size(self, account_value, price, win_rate, avg_win, avg_loss):
        """
        计算买入数量
        """
        # 计算凯利比例
        kelly_fraction = self.calculate_kelly_fraction(win_rate, avg_win, avg_loss)

        # 凯利公式通常过于激进，实际使用时通常会乘以一个缩减因子（如0.5）
        reduced_kelly = kelly_fraction * 0.5

        # 可用资金
        available_cash = account_value * reduced_kelly

        # 计算可买入数量
        position_size = int(available_cash / price)

        return position_size, reduced_kelly

# 使用示例
manager = KellyPositionManager()
account_value = 1000000
price = 100.0
win_rate = 0.6      # 60%胜率
avg_win = 5000      # 平均盈利5000元
avg_loss = 3000     # 平均亏损3000元

position_size, kelly_fraction = manager.calculate_position_size(
    account_value, price, win_rate, avg_win, avg_loss
)
print(f"凯利比例: {kelly_fraction:.2%}")
print(f"买入数量: {position_size}股")
print(f"使用资金: {position_size * price:,.2f}元")
```

### 2.3 波动率调整仓位
```python
import numpy as np

class VolatilityAdjustedPositionManager:
    def __init__(self, base_position_ratio=0.1, target_volatility=0.02):
        """
        波动率调整仓位管理

        base_position_ratio: 基础仓位比例
        target_volatility: 目标波动率（日波动率）
        """
        self.base_position_ratio = base_position_ratio
        self.target_volatility = target_volatility

    def calculate_volatility(self, prices, period=20):
        """
        计算波动率
        """
        returns = prices.pct_change().dropna()
        volatility = returns.rolling(window=period).std().iloc[-1]

        return volatility

    def calculate_position_size(self, account_value, price, prices):
        """
        计算买入数量
        """
        # 计算波动率
        volatility = self.calculate_volatility(prices)

        # 波动率调整因子
        # 高波动低仓位，低波动高仓位
        adjustment_factor = self.target_volatility / volatility
        adjustment_factor = max(0.5, min(2.0, adjustment_factor))  # 限制在0.5-2.0之间

        # 调整后的仓位比例
        adjusted_position_ratio = self.base_position_ratio * adjustment_factor

        # 可用资金
        available_cash = account_value * adjusted_position_ratio

        # 计算可买入数量
        position_size = int(available_cash / price)

        return position_size, adjusted_position_ratio

# 使用示例
import pandas as pd

manager = VolatilityAdjustedPositionManager(base_position_ratio=0.1, target_volatility=0.02)
account_value = 1000000
price = 100.0

# 模拟价格数据
prices = pd.Series([100, 102, 105, 108, 110, 108, 106, 105, 104, 103,
                    105, 107, 110, 112, 115, 118, 120, 122, 125, 128])

position_size, adjusted_ratio = manager.calculate_position_size(account_value, price, prices)
print(f"调整后仓位比例: {adjusted_ratio:.2%}")
print(f"买入数量: {position_size}股")
print(f"使用资金: {position_size * price:,.2f}元")
```

### 2.4 风险平价仓位
```python
class RiskParityPositionManager:
    def __init__(self):
        """
        风险平价仓位管理
        使各资产的风险贡献相等
        """
        pass

    def calculate_covariance(self, returns):
        """
        计算协方差矩阵
        """
        return returns.cov()

    def calculate_position_weights(self, returns):
        """
        计算风险平价权重

        目标: w_i * σ_i = w_j * σ_j （所有资产的风险贡献相等）
        """
        # 计算协方差矩阵
        cov_matrix = self.calculate_covariance(returns)

        # 计算波动率
        volatilities = np.sqrt(np.diag(cov_matrix))

        # 风险平价权重：与波动率成反比
        weights = 1 / volatilities
        weights = weights / weights.sum()  # 归一化

        return weights

    def calculate_position_sizes(self, account_value, prices, returns):
        """
        计算各资产的买入数量
        """
        # 计算权重
        weights = self.calculate_position_weights(returns)

        # 计算各资产的买入数量
        position_sizes = {}
        for asset, price in prices.items():
            available_cash = account_value * weights[asset]
            position_sizes[asset] = int(available_cash / price)

        return position_sizes, weights

# 使用示例
manager = RiskParityPositionManager()
account_value = 1000000

# 模拟价格和收益数据
prices = {
    'stock1': pd.Series([100, 102, 105, 108, 110]),
    'stock2': pd.Series([50, 51, 53, 55, 56]),
    'stock3': pd.Series([80, 82, 85, 88, 90])
}

returns = pd.DataFrame({
    'stock1': [0.02, 0.029, 0.029, 0.019],
    'stock2': [0.02, 0.039, 0.038, 0.018],
    'stock3': [0.025, 0.037, 0.035, 0.023]
})

position_sizes, weights = manager.calculate_position_sizes(account_value, prices, returns)
print("风险平价权重:")
for asset, weight in weights.items():
    print(f"{asset}: {weight:.2%}")

print("\n买入数量:")
for asset, size in position_sizes.items():
    print(f"{asset}: {size}股")
```

---

## 三、止损止盈

### 3.1 固定百分比止损
```python
class FixedPercentStopLoss:
    def __init__(self, stop_loss_percent=0.05, take_profit_percent=0.10):
        """
        固定百分比止损止盈

        stop_loss_percent: 止损百分比（如0.05表示5%）
        take_profit_percent: 止盈百分比（如0.10表示10%）
        """
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_percent = take_profit_percent

    def calculate_stop_price(self, entry_price):
        """
        计算止损价
        """
        stop_loss_price = entry_price * (1 - self.stop_loss_percent)
        return stop_loss_price

    def calculate_take_profit_price(self, entry_price):
        """
        计算止盈价
        """
        take_profit_price = entry_price * (1 + self.take_profit_percent)
        return take_profit_price

    def check_stop_loss(self, current_price, entry_price):
        """
        检查是否触发止损
        """
        stop_loss_price = self.calculate_stop_price(entry_price)
        return current_price <= stop_loss_price

    def check_take_profit(self, current_price, entry_price):
        """
        检查是否触发止盈
        """
        take_profit_price = self.calculate_take_profit_price(entry_price)
        return current_price >= take_profit_price

# 使用示例
manager = FixedPercentStopLoss(stop_loss_percent=0.05, take_profit_percent=0.10)
entry_price = 100.0

stop_loss_price = manager.calculate_stop_price(entry_price)
take_profit_price = manager.calculate_take_profit_price(entry_price)

print(f"买入价: {entry_price}元")
print(f"止损价: {stop_loss_price:.2f}元")
print(f"止盈价: {take_profit_price:.2f}元")

# 检查
current_price = 95.0
if manager.check_stop_loss(current_price, entry_price):
    print(f"触发止损！当前价格: {current_price}元")
```

### 3.2 ATR止损
```python
class ATRStopLoss:
    def __init__(self, atr_period=14, atr_multiplier=2):
        """
        ATR止损

        atr_period: ATR周期
        atr_multiplier: ATR倍数（通常2-3）
        """
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier

    def calculate_atr(self, high, low, close):
        """
        计算ATR（平均真实波幅）
        """
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.atr_period).mean()

        return atr

    def calculate_stop_price(self, entry_price, high, low, close):
        """
        计算ATR止损价
        """
        # 计算ATR
        atr = self.calculate_atr(high, low, close)
        current_atr = atr.iloc[-1]

        # 止损距离 = N * ATR
        stop_distance = self.atr_multiplier * current_atr

        # 止损价
        stop_loss_price = entry_price - stop_distance

        return stop_loss_price, current_atr

    def update_trailing_stop(self, current_price, previous_stop_price, high, low, close):
        """
        更新移动止损
        """
        # 计算新的止损价
        stop_loss_price, atr = self.calculate_stop_price(current_price, high, low, close)

        # 移动止损：只向上移动，不向下移动
        new_stop_price = max(previous_stop_price, stop_loss_price)

        return new_stop_price

# 使用示例
import pandas as pd

manager = ATRStopLoss(atr_period=14, atr_multiplier=2)

# 模拟数据
data = pd.DataFrame({
    'high': [105, 107, 110, 112, 115, 118, 120, 122, 125, 128],
    'low': [98, 100, 103, 106, 109, 112, 115, 117, 120, 123],
    'close': [100, 102, 105, 108, 110, 108, 106, 105, 104, 103]
})

entry_price = 100.0

# 计算ATR止损价
stop_loss_price, atr = manager.calculate_stop_price(
    entry_price, data['high'], data['low'], data['close']
)

print(f"买入价: {entry_price}元")
print(f"ATR: {atr:.2f}")
print(f"止损价: {stop_loss_price:.2f}元")

# 移动止损示例
current_price = 110.0
previous_stop_price = stop_loss_price

new_stop_price = manager.update_trailing_stop(
    current_price, previous_stop_price,
    data['high'], data['low'], data['close']
)

print(f"\n当前价格: {current_price}元")
print(f"移动止损价: {new_stop_price:.2f}元")
```

### 3.3 移动止损
```python
class TrailingStopLoss:
    def __init__(self, trailing_percent=0.05):
        """
        移动止损

        trailing_percent: 移动止损百分比（如0.05表示5%）
        """
        self.trailing_percent = trailing_percent
        self.highest_price = None
        self.stop_loss_price = None

    def update(self, current_price):
        """
        更新移动止损

        止损价 = 最高价 * (1 - trailing_percent)
        如果当前价格创新高，更新最高价和止损价
        """
        if self.highest_price is None or current_price > self.highest_price:
            # 价格创新高，更新最高价和止损价
            self.highest_price = current_price
            self.stop_loss_price = current_price * (1 - self.trailing_percent)

        return self.stop_loss_price

    def check_stop_loss(self, current_price):
        """
        检查是否触发止损
        """
        if self.stop_loss_price is None:
            return False

        return current_price <= self.stop_loss_price

    def reset(self):
        """
        重置
        """
        self.highest_price = None
        self.stop_loss_price = None

# 使用示例
manager = TrailingStopLoss(trailing_percent=0.05)

prices = [100, 102, 105, 108, 110, 108, 106, 105, 104, 103]

for i, price in enumerate(prices):
    stop_loss_price = manager.update(price)
    print(f"第{i+1}天 价格: {price:.2f}元, 止损价: {stop_loss_price:.2f}元")

    if manager.check_stop_loss(price):
        print(f"触发止损！在第{i+1}天")
        break
```

---

## 四、风险控制指标

### 4.1 VaR（Value at Risk）
```python
import numpy as np
from scipy.stats import norm

class VaRCalculator:
    def __init__(self):
        """
        VaR（在险价值）计算器

        VaR: 在一定置信度下，资产或投资组合在未来特定时间内可能遭受的最大损失
        """
        pass

    def calculate_historical_var(self, returns, confidence_level=0.95):
        """
        历史模拟法计算VaR

        returns: 收益率序列
        confidence_level: 置信水平（如0.95表示95%置信度）
        """
        # 计算分位数
        var_percentile = 1 - confidence_level
        var = np.percentile(returns, var_percentile * 100)

        return var

    def calculate_parametric_var(self, returns, portfolio_value, confidence_level=0.95, time_horizon=1):
        """
        参数法计算VaR

        假设收益率服从正态分布
        VaR = portfolio_value * (μ - z_α * σ * sqrt(t))
        """
        # 计算收益率均值和标准差
        mu = returns.mean()
        sigma = returns.std()

        # 计算z分数
        z_score = norm.ppf(1 - confidence_level)

        # 计算VaR
        var = portfolio_value * (mu - z_score * sigma * np.sqrt(time_horizon))

        return var

    def calculate_cvar(self, returns, confidence_level=0.95):
        """
        CVaR（条件VaR，也叫Expected Shortfall）

        CVaR: 超过VaR时的平均损失
        """
        # 计算VaR
        var = self.calculate_historical_var(returns, confidence_level)

        # 计算CVaR
        cvar = returns[returns <= var].mean()

        return cvar

# 使用示例
import pandas as pd

calculator = VaRCalculator()

# 模拟收益率数据
np.random.seed(42)
returns = pd.Series(np.random.normal(0, 0.02, 252))  # 一年252个交易日
portfolio_value = 1000000  # 100万投资组合

# 历史模拟法VaR
var_historical = calculator.calculate_historical_var(returns, confidence_level=0.95)
print(f"历史模拟法VaR (95%): {var_historical:.4f} ({var_historical:.2%})")
print(f"最大可能损失: {portfolio_value * abs(var_historical):,.2f}元")

# 参数法VaR
var_parametric = calculator.calculate_parametric_var(
    returns, portfolio_value, confidence_level=0.95
)
print(f"\n参数法VaR (95%): {var_parametric:,.2f}元")

# CVaR
cvar = calculator.calculate_cvar(returns, confidence_level=0.95)
print(f"\nCVaR (95%): {cvar:.4f} ({cvar:.2%})")
print(f"条件最大损失: {portfolio_value * abs(cvar):,.2f}元")
```

### 4.2 最大回撤
```python
class DrawDownCalculator:
    def __init__(self):
        """
        最大回撤计算器
        """
        pass

    def calculate_drawdown(self, equity_curve):
        """
        计算回撤

        equity_curve: 资金曲线
        """
        # 计算累计净值
        cummax = equity_curve.expanding().max()

        # 计算回撤
        drawdown = (equity_curve - cummax) / cummax

        return drawdown

    def calculate_max_drawdown(self, equity_curve):
        """
        计算最大回撤
        """
        drawdown = self.calculate_drawdown(equity_curve)
        max_drawdown = drawdown.min()

        return max_drawdown

    def calculate_max_drawdown_duration(self, equity_curve):
        """
        计算最大回撤持续时间
        """
        drawdown = self.calculate_drawdown(equity_curve)

        # 找到回撤开始的索引
        max_dd_idx = drawdown.idxmin()

        # 找到回撤开始前的最高点
        cummax = equity_curve.expanding().max()
        peak_idx = equity_curve[:max_dd_idx].idxmax()

        # 计算回撤持续时间（天数）
        duration = (max_dd_idx - peak_idx).days

        return duration

# 使用示例
import pandas as pd

calculator = DrawDownCalculator()

# 模拟资金曲线
dates = pd.date_range(start='2023-01-01', periods=252)
equity_curve = pd.Series(
    [1000000 * (1 + i * 0.001 + np.random.randn() * 0.02) for i in range(252)],
    index=dates
)

# 计算回撤
drawdown = calculator.calculate_drawdown(equity_curve)

# 计算最大回撤
max_drawdown = calculator.calculate_max_drawdown(equity_curve)
print(f"最大回撤: {max_drawdown:.2%}")

# 计算最大回撤持续时间
duration = calculator.calculate_max_drawdown_duration(equity_curve)
print(f"最大回撤持续时间: {duration}天")
```

### 4.3 夏普比率
```python
class SharpeRatioCalculator:
    def __init__(self, risk_free_rate=0.03):
        """
        夏普比率计算器

        Sharpe Ratio = (E[R] - Rf) / σ(R)

        E[R]: 预期收益率
        Rf: 无风险利率
        σ(R): 收益率标准差
        """
        self.risk_free_rate = risk_free_rate

    def calculate_sharpe_ratio(self, returns, periods=252):
        """
        计算夏普比率

        returns: 收益率序列
        periods: 一年中的周期数（日收益率为252）
        """
        # 计算年化收益率
        annual_return = returns.mean() * periods

        # 计算年化波动率
        annual_volatility = returns.std() * np.sqrt(periods)

        # 计算超额收益
        excess_return = annual_return - self.risk_free_rate

        # 计算夏普比率
        sharpe_ratio = excess_return / annual_volatility

        return sharpe_ratio

    def calculate_sortino_ratio(self, returns, risk_free_rate=0.03, periods=252):
        """
        计算索提诺比率

        Sortino Ratio = (E[R] - Rf) / σd(R)

        σd(R): 下行标准差（只考虑负收益的波动率）
        """
        # 计算年化收益率
        annual_return = returns.mean() * periods

        # 计算下行收益
        downside_returns = returns[returns < 0]

        # 计算下行波动率
        if len(downside_returns) > 0:
            downside_volatility = downside_returns.std() * np.sqrt(periods)
        else:
            downside_volatility = 0

        # 计算超额收益
        excess_return = annual_return - risk_free_rate

        # 计算索提诺比率
        sortino_ratio = excess_return / downside_volatility if downside_volatility != 0 else 0

        return sortino_ratio

    def calculate_calmar_ratio(self, returns, equity_curve, periods=252):
        """
        计算卡尔玛比率

        Calmar Ratio = 年化收益率 / 最大回撤
        """
        # 计算年化收益率
        annual_return = returns.mean() * periods

        # 计算最大回撤
        drawdown_calculator = DrawDownCalculator()
        max_drawdown = abs(drawdown_calculator.calculate_max_drawdown(equity_curve))

        # 计算卡尔玛比率
        calmar_ratio = annual_return / max_drawdown if max_drawdown != 0 else 0

        return calmar_ratio

# 使用示例
import pandas as pd

calculator = SharpeRatioCalculator(risk_free_rate=0.03)

# 模拟收益率数据
np.random.seed(42)
returns = pd.Series(np.random.normal(0.0005, 0.02, 252))

# 模拟资金曲线
equity_curve = (1 + returns).cumprod() * 1000000

# 计算夏普比率
sharpe_ratio = calculator.calculate_sharpe_ratio(returns)
print(f"夏普比率: {sharpe_ratio:.4f}")
# 夏普比率 > 1.0: 良好
# 夏普比率 > 2.0: 优秀

# 计算索提诺比率
sortino_ratio = calculator.calculate_sortino_ratio(returns)
print(f"索提诺比率: {sortino_ratio:.4f}")

# 计算卡尔玛比率
calmar_ratio = calculator.calculate_calmar_ratio(returns, equity_curve)
print(f"卡尔玛比率: {calmar_ratio:.4f}")
```

---

## 五、综合风控系统

### 5.1 完整风控系统
```python
class RiskManagementSystem:
    def __init__(self, config):
        """
        综合风控系统

        config: 风控配置
        """
        # 仓位管理
        self.position_manager = self._init_position_manager(config.get('position', {}))

        # 止损止盈
        self.stop_loss_manager = self._init_stop_loss_manager(config.get('stop_loss', {}))

        # 风险指标
        self.var_calculator = VaRCalculator()
        self.drawdown_calculator = DrawDownCalculator()
        self.ratio_calculator = SharpeRatioCalculator(
            risk_free_rate=config.get('risk_free_rate', 0.03)
        )

        # 风控参数
        self.max_position_ratio = config.get('max_position_ratio', 0.2)  # 单股最大仓位
        self.max_total_position = config.get('max_total_position', 0.8)  # 总仓位上限
        self.max_drawdown_limit = config.get('max_drawdown_limit', 0.15)  # 最大回撤限制
        self.daily_loss_limit = config.get('daily_loss_limit', 0.03)  # 单日最大亏损限制

        # 状态
        self.current_positions = {}
        self.equity_curve = []

    def _init_position_manager(self, config):
        """
        初始化仓位管理器
        """
        method = config.get('method', 'fixed')

        if method == 'fixed':
            return FixedPositionManager(position_ratio=config.get('ratio', 0.1))
        elif method == 'kelly':
            return KellyPositionManager()
        elif method == 'volatility':
            return VolatilityAdjustedPositionManager(
                base_position_ratio=config.get('base_ratio', 0.1),
                target_volatility=config.get('target_volatility', 0.02)
            )
        else:
            return FixedPositionManager(position_ratio=0.1)

    def _init_stop_loss_manager(self, config):
        """
        初始化止损止盈管理器
        """
        method = config.get('method', 'fixed_percent')

        if method == 'fixed_percent':
            return FixedPercentStopLoss(
                stop_loss_percent=config.get('stop_loss', 0.05),
                take_profit_percent=config.get('take_profit', 0.10)
            )
        elif method == 'atr':
            return ATRStopLoss(
                atr_period=config.get('atr_period', 14),
                atr_multiplier=config.get('atr_multiplier', 2)
            )
        elif method == 'trailing':
            return TrailingStopLoss(trailing_percent=config.get('trailing', 0.05))
        else:
            return FixedPercentStopLoss(stop_loss_percent=0.05, take_profit_percent=0.10)

    def check_entry_signal(self, account_value, price, stock_data):
        """
        检查是否可以买入
        """
        # 检查总仓位
        total_position = sum([p['size'] * p['current_price'] for p in self.current_positions.values()])
        total_position_ratio = total_position / account_value

        if total_position_ratio >= self.max_total_position:
            print(f"总仓位已达上限: {total_position_ratio:.2%}")
            return False

        # 检查单股仓位
        position_size = self.position_manager.calculate_position_size(account_value, price, stock_data)
        position_value = position_size * price
        position_ratio = position_value / account_value

        if position_ratio > self.max_position_ratio:
            print(f"单股仓位过大: {position_ratio:.2%}，上限: {self.max_position_ratio:.2%}")
            return False

        return True

    def check_exit_signal(self, position, current_price):
        """
        检查是否需要卖出
        """
        stock_code = position['stock_code']
        entry_price = position['entry_price']
        stop_loss_price = position.get('stop_loss_price')
        take_profit_price = position.get('take_profit_price')

        # 检查止损
        if stop_loss_price and current_price <= stop_loss_price:
            print(f"{stock_code} 触发止损！当前价格: {current_price:.2f}，止损价: {stop_loss_price:.2f}")
            return 'stop_loss'

        # 检查止盈
        if take_profit_price and current_price >= take_profit_price:
            print(f"{stock_code} 触发止盈！当前价格: {current_price:.2f}，止盈价: {take_profit_price:.2f}")
            return 'take_profit'

        return False

    def check_risk_limits(self, account_value, daily_returns):
        """
        检查风险限制
        """
        # 检查单日亏损
        if len(daily_returns) > 0:
            daily_loss = daily_returns[-1]
            if daily_loss < -self.daily_loss_limit:
                print(f"触发单日亏损限制！单日亏损: {daily_loss:.2%}，限制: {-self.daily_loss_limit:.2%}")
                return False

        # 检查最大回撤
        if len(self.equity_curve) > 20:
            equity_curve_series = pd.Series(self.equity_curve)
            max_drawdown = self.drawdown_calculator.calculate_max_drawdown(equity_curve_series)

            if abs(max_drawdown) > self.max_drawdown_limit:
                print(f"触发最大回撤限制！当前回撤: {abs(max_drawdown):.2%}，限制: {self.max_drawdown_limit:.2%}")
                return False

        return True

    def update_position(self, stock_code, action, price, size, **kwargs):
        """
        更新持仓
        """
        if action == 'buy':
            self.current_positions[stock_code] = {
                'stock_code': stock_code,
                'entry_price': price,
                'current_price': price,
                'size': size,
                'entry_time': pd.Timestamp.now(),
                'stop_loss_price': kwargs.get('stop_loss_price'),
                'take_profit_price': kwargs.get('take_profit_price')
            }

        elif action == 'sell':
            if stock_code in self.current_positions:
                del self.current_positions[stock_code]

    def update_equity(self, equity):
        """
        更新资金曲线
        """
        self.equity_curve.append(equity)

    def get_risk_report(self):
        """
        获取风险报告
        """
        if len(self.equity_curve) < 2:
            return None

        equity_curve_series = pd.Series(self.equity_curve)
        returns = equity_curve_series.pct_change().dropna()

        # 计算各项指标
        sharpe_ratio = self.ratio_calculator.calculate_sharpe_ratio(returns)
        sortino_ratio = self.ratio_calculator.calculate_sortino_ratio(returns)
        calmar_ratio = self.ratio_calculator.calculate_calmar_ratio(returns, equity_curve_series)
        max_drawdown = self.drawdown_calculator.calculate_max_drawdown(equity_curve_series)
        var_95 = self.var_calculator.calculate_historical_var(returns, confidence_level=0.95)
        cvar_95 = self.var_calculator.calculate_cvar(returns, confidence_level=0.95)

        report = {
            '夏普比率': sharpe_ratio,
            '索提诺比率': sortino_ratio,
            '卡尔玛比率': calmar_ratio,
            '最大回撤': max_drawdown,
            'VaR (95%)': var_95,
            'CVaR (95%)': cvar_95,
            '当前持仓数': len(self.current_positions),
            '资金曲线': equity_curve_series
        }

        return report

# 使用示例
# 风控配置
config = {
    'position': {
        'method': 'volatility',
        'base_ratio': 0.1,
        'target_volatility': 0.02
    },
    'stop_loss': {
        'method': 'atr',
        'atr_period': 14,
        'atr_multiplier': 2
    },
    'risk_free_rate': 0.03,
    'max_position_ratio': 0.2,
    'max_total_position': 0.8,
    'max_drawdown_limit': 0.15,
    'daily_loss_limit': 0.03
}

# 创建风控系统
risk_system = RiskManagementSystem(config)

# 检查买入信号
account_value = 1000000
price = 100.0
stock_data = pd.Series([100, 102, 105, 108, 110])

if risk_system.check_entry_signal(account_value, price, stock_data):
    print("可以买入")

    # 计算买入数量
    position_size = risk_system.position_manager.calculate_position_size(account_value, price, stock_data)
    print(f"买入数量: {position_size}股")

    # 计算止损止盈价
    stop_loss_price, _ = risk_system.stop_loss_manager.calculate_stop_price(
        price, stock_data, stock_data, stock_data
    )

    # 更新持仓
    risk_system.update_position(
        stock_code='000001',
        action='buy',
        price=price,
        size=position_size,
        stop_loss_price=stop_loss_price
    )
```

---

## 六、最佳实践

### 6.1 风控原则
1. **永远设置止损**：每笔交易都必须有止损
2. **控制仓位**：单股仓位不超过20%，总仓位不超过80%
3. **分散投资**：不要把鸡蛋放在一个篮子里
4. **定期评估**：定期检查风险指标，及时调整策略

### 6.2 风险指标标准
| 指标 | 优秀 | 良好 | 一般 | 较差 |
|------|------|------|------|------|
| 夏普比率 | > 2.0 | 1.5-2.0 | 1.0-1.5 | < 1.0 |
| 最大回撤 | < 10% | 10%-15% | 15%-20% | > 20% |
| 卡尔玛比率 | > 1.0 | 0.5-1.0 | 0.3-0.5 | < 0.3 |
| 胜率 | > 60% | 50%-60% | 40%-50% | < 40% |

### 6.3 常见错误
1. **不设置止损**：小亏损变大亏损
2. **仓位过重**：单笔交易亏损影响整体
3. **过度自信**：忽视风险，加大杠杆
4. **追涨杀跌**：情绪化交易

---

*学习笔记持续更新中...*
*最后更新：2026年4月11日*
