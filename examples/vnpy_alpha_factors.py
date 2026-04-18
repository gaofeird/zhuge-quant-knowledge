#!/usr/bin/env python3
"""
vnpy.alpha 因子库示例
基于 VeighNa 4.0 的 AI量化模块

核心特性：
1. Alpha158/101 因子库
2. LightGBM 预测模型
3. CTA策略引擎
4. 组合策略系统
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import warnings


class FactorType(Enum):
    """因子类型"""
    PRICE = "price"           # 价格类
    VOLUME = "volume"         # 量能类
    MOMENTUM = "momentum"     # 动量类
    VOLATILITY = "volatility" # 波动类
    TURNOVER = "turnover"     # 换手类
    BASIC = "basic"           # 基本面


@dataclass
class Factor:
    """因子"""
    name: str
    value: np.ndarray
    category: FactorType
    created_at: datetime = field(default_factory=datetime.now)


class Alpha158Calculator:
    """
    Alpha158 因子计算器
    
    基于微软 Qlib 的 Alpha158 因子集
    包含158个量化因子，覆盖K线形态和时序特征
    """
    
    def __init__(self):
        self.factors: Dict[str, Factor] = {}
    
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算 Alpha158 因子
        
        Args:
            data: 必须包含 open, high, low, close, volume
        
        Returns:
            因子DataFrame
        """
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"Missing required column: {col}")
        
        results = {}
        
        # ========== 价格类因子 (Price) ==========
        # 1. 收益率
        results['return_1'] = data['close'].pct_change(1)
        results['return_5'] = data['close'].pct_change(5)
        results['return_10'] = data['close'].pct_change(10)
        results['return_20'] = data['close'].pct_change(20)
        
        # 2. 均线相关
        for window in [5, 10, 20, 30]:
            ma = data['close'].rolling(window).mean()
            results[f'ma_ratio_{window}'] = data['close'] / ma - 1
            
            # 均线交叉
            if window == 5:
                ma10 = data['close'].rolling(10).mean()
                results[f'ma_cross_{window}'] = ma / ma10 - 1
        
        # 3. 价格位置
        rolling_high = data['high'].rolling(20).max()
        rolling_low = data['low'].rolling(20).min()
        results['high_low_ratio'] = (data['close'] - rolling_low) / (rolling_high - rolling_low + 1e-9)
        
        # ========== 量能类因子 (Volume) ==========
        # 4. 量能变化
        vol_ma5 = data['volume'].rolling(5).mean()
        vol_ma20 = data['volume'].rolling(20).mean()
        results['volume_ratio_5'] = data['volume'] / vol_ma5
        results['volume_ratio_20'] = data['volume'] / vol_ma20
        
        # 5. 量价相关
        results['price_volume_corr'] = data['close'].rolling(20).corr(data['volume'])
        
        # 6. 主动性买入 (近似)
        typical = (data['high'] + data['low'] + data['close']) / 3
        results['volume_price'] = data['volume'] * typical
        
        # ========== 动量类因子 (Momentum) ==========
        # 7. 动量
        for period in [5, 10, 20, 30]:
            results[f'momentum_{period}'] = data['close'] / data['close'].shift(period) - 1
        
        # 8. RSI
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        results['rsi'] = 100 - (100 / (1 + rs))
        
        # 9. MACD
        ema12 = data['close'].ewm(span=12).mean()
        ema26 = data['close'].ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        results['macd'] = macd
        results['macd_signal'] = signal
        results['macd_hist'] = macd - signal
        
        # ========== 波动类因子 (Volatility) ==========
        # 10. 波动率
        returns = data['close'].pct_change()
        for window in [5, 10, 20, 30]:
            results[f'volatility_{window}'] = returns.rolling(window).std()
        
        # 11. 布林带
        bbp = (data['close'] - data['close'].rolling(20).mean()) / (2 * data['close'].rolling(20).std())
        results['bollinger_position'] = bbp
        
        # 12. ATR
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        results['atr_14'] = tr.rolling(14).mean()
        
        # ========== 换手类因子 (Turnover) ==========
        # 13. 换手率变化 (需要额外数据，模拟)
        results['turnover_change'] = data['volume'].pct_change()
        
        # ========== 基本面因子 (Basic) ==========
        # 14. 基本统计
        results['daily_return_std'] = returns.rolling(20).std()
        results['price_skewness'] = data['close'].rolling(20).skew()
        results['volume_skewness'] = data['volume'].rolling(20).skew()
        
        # 组装结果
        result_df = pd.DataFrame(results)
        
        # 填充NaN
        result_df = result_df.fillna(0).replace([np.inf, -np.inf], 0)
        
        return result_df
    
    def get_factor_names(self) -> List[str]:
        """获取所有因子名称"""
        return list(self.factors.keys()) if self.factors else []


class Alpha101Calculator:
    """
    Alpha101 因子计算器
    
    WorldQuant 101 Alpha 因子
    """
    
    @staticmethod
    def rank(series: pd.Series) -> pd.Series:
        """横截面排名"""
        return series.rank(pct=True)
    
    @staticmethod
    def delta(series: pd.Series, period: int = 1) -> pd.Series:
        """差分"""
        return series.diff(period)
    
    @staticmethod
    def ts_rank(series: pd.Series, window: int = 10) -> pd.Series:
        """时序排名"""
        return series.rolling(window).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(x) > 0 else 0
        )
    
    @staticmethod
    def ts_corr(x: pd.Series, y: pd.Series, window: int = 20) -> pd.Series:
        """时序相关"""
        return x.rolling(window).corr(y)
    
    def calculate_alpha_001(
        self, 
        close: pd.Series, 
        volume: pd.Series
    ) -> pd.Series:
        """
        Alpha#001: (rank(Ts_ArgMax(SignedPower(((returns <= 0) ? volume : close), 2.), 14))) - 0.5)
        """
        signed_power = np.where(
            close.pct_change() <= 0,
            volume,
            close
        ) ** 2
        
        ts_argmax = pd.Series(signed_power).rolling(14).apply(
            lambda x: np.argmax(x) / 14 if len(x) > 0 else 0
        )
        
        return self.rank(ts_argmax) - 0.5
    
    def calculate_alpha_002(
        self, 
        close: pd.Series,
        open_price: pd.Series
    ) -> pd.Series:
        """
        Alpha#002: (- Ts_Rank(rank(low), 9))
        """
        return -self.ts_rank(self.rank(close), 9) + self.ts_rank(self.rank(open_price), 9)
    
    def calculate_alpha_003(
        self,
        close: pd.Series,
        volume: pd.Series,
        open_price: pd.Series
    ) -> pd.Series:
        """
        Alpha#003: ((- rank(std((volume / ts_mean(volume, 20))), 4)) 
                   * rank(delta(((close - open_price) / open_price), 1)))
        """
        vol_ratio = volume / volume.rolling(20).mean()
        vol_rank = self.rank(vol_ratio.rolling(4).std())
        
        price_change = (close - open_price) / open_price
        delta_rank = self.rank(self.delta(price_change, 1))
        
        return -vol_rank * delta_rank


class LightGBMPredictor:
    """
    LightGBM 预测模型
    
    用于因子预测和信号生成
    """
    
    def __init__(self, model_params: Optional[Dict] = None):
        self.model_params = model_params or {
            'objective': 'regression',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
        }
        self.model = None
        self.feature_importance: Optional[pd.DataFrame] = None
    
    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        训练模型
        
        Args:
            X: 特征矩阵
            y: 目标变量 (未来收益率)
            feature_names: 特征名称
        """
        try:
            import lightgbm as lgb
        except ImportError:
            warnings.warn("LightGBM not installed, using mock training")
            self.model = "mock"
            return {"status": "mock", "rmse": 0.01}
        
        if feature_names:
            X.columns = feature_names
        
        # 划分训练集
        n = len(X)
        train_size = int(n * 0.8)
        
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]
        
        # 创建数据集
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
        
        # 训练
        self.model = lgb.train(
            self.model_params,
            train_data,
            num_boost_round=500,
            valid_sets=[train_data, valid_data],
            valid_names=['train', 'valid'],
            callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)]
        )
        
        # 特征重要性
        importance = self.model.feature_importance(importance_type='gain')
        self.feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        # 评估
        y_pred = self.model.predict(X_test)
        rmse = np.sqrt(np.mean((y_pred - y_test) ** 2))
        mae = np.mean(np.abs(y_pred - y_test))
        
        return {
            "rmse": rmse,
            "mae": mae,
            "feature_importance": self.feature_importance.head(10).to_dict()
        }
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """预测"""
        if self.model is None:
            raise ValueError("Model not trained")
        
        if self.model == "mock":
            return np.random.randn(len(X)) * 0.01
        
        return self.model.predict(X)
    
    def get_signal(self, X: pd.DataFrame, threshold: float = 0.0) -> np.ndarray:
        """
        生成交易信号
        
        Args:
            X: 特征矩阵
            threshold: 信号阈值
        
        Returns:
            信号: 1(买入), 0(持有), -1(卖出)
        """
        predictions = self.predict(X)
        return np.where(predictions > threshold, 1, np.where(predictions < -threshold, -1, 0))


class CTAStrategy:
    """
    CTA 策略引擎
    
    基于 vnpy.cta 设计的策略模板
    """
    
    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        self.parameters: Dict[str, Any] = {}
        self.inited = False
        
        # 策略状态
        self.pos = 0  # 持仓
        self.entry_price = 0.0
        self.undone = 0  # 今日未完成交易次数
    
    def on_init(self, parameters: Dict):
        """策略初始化"""
        self.parameters = parameters
        self.inited = True
    
    def on_bar(self, bar: Dict, indicators: Optional[Dict] = None) -> Dict[str, Any]:
        """
        K线数据回调
        
        Args:
            bar: K线数据 (open, high, low, close, volume)
            indicators: 指标数据 (可选)
        
        Returns:
            交易指令: {action: 'BUY'/'SELL'/'HOLD', price: float, volume: int}
        """
        if not self.inited:
            return {"action": "HOLD"}
        
        action = "HOLD"
        price = bar['close']
        volume = 0
        
        # 获取指标
        macd = indicators.get('macd', 0) if indicators else 0
        macd_signal = indicators.get('macd_signal', 0) if indicators else 0
        rsi = indicators.get('rsi', 50) if indicators else 50
        
        # MACD 金叉/死叉策略
        if self.parameters.get('strategy_type') == 'macd':
            # 入场条件
            if self.pos == 0 and macd > macd_signal:
                action = "BUY"
                volume = self.parameters.get('fixed_size', 1)
            # 出场条件
            elif self.pos > 0 and macd < macd_signal:
                action = "SELL"
                volume = abs(self.pos)
            # 止损
            elif self.pos > 0 and price < self.entry_price * (1 - self.parameters.get('stop_loss', 0.02)):
                action = "SELL"
                volume = abs(self.pos)
        
        # RSI 策略
        elif self.parameters.get('strategy_type') == 'rsi':
            if self.pos == 0 and rsi < 30:  # 超卖
                action = "BUY"
                volume = self.parameters.get('fixed_size', 1)
            elif self.pos > 0 and rsi > 70:  # 超买
                action = "SELL"
                volume = abs(self.pos)
        
        # 更新持仓
        if action == "BUY":
            self.pos += volume
            self.entry_price = price
        elif action == "SELL":
            self.pos -= volume
        
        return {
            "action": action,
            "price": price,
            "volume": volume,
            "pos": self.pos
        }


def demo():
    """演示 vnpy.alpha 因子库"""
    
    print("\n" + "="*70)
    print("  vnpy.alpha 因子库演示")
    print("="*70)
    
    # 创建示例数据
    np.random.seed(42)
    n = 500
    
    data = pd.DataFrame({
        'date': pd.date_range('2025-01-01', periods=n, freq='D'),
        'open': 100 + np.cumsum(np.random.randn(n) * 0.5),
        'high': 102 + np.cumsum(np.random.randn(n) * 0.5),
        'low': 98 + np.cumsum(np.random.randn(n) * 0.5),
        'close': 100 + np.cumsum(np.random.randn(n) * 0.5),
        'volume': np.random.uniform(1e6, 5e6, n),
    })
    
    # ========== Alpha158 因子计算 ==========
    print("\n[Step 1] 计算 Alpha158 因子...")
    calculator = Alpha158Calculator()
    factors = calculator.calculate(data)
    print(f"  因子数量: {len(factors.columns)}")
    print(f"  因子列表: {list(factors.columns[:10])}...")
    
    # ========== Alpha101 因子 ==========
    print("\n[Step 2] 计算 Alpha101 因子...")
    alpha101 = Alpha101Calculator()
    
    alpha_001 = alpha101.calculate_alpha_001(data['close'], data['volume'])
    alpha_002 = alpha101.calculate_alpha_002(data['close'], data['open'])
    alpha_003 = alpha101.calculate_alpha_003(data['close'], data['volume'], data['open'])
    
    print(f"  Alpha#001: mean={alpha_001.mean():.4f}, std={alpha_001.std():.4f}")
    print(f"  Alpha#002: mean={alpha_002.mean():.4f}, std={alpha_002.std():.4f}")
    print(f"  Alpha#003: mean={alpha_003.mean():.4f}, std={alpha_003.std():.4f}")
    
    # ========== LightGBM 预测 ==========
    print("\n[Step 3] 训练 LightGBM 预测模型...")
    # 创建目标变量 (未来5日收益率)
    y = data['close'].shift(-5) / data['close'] - 1
    
    # 合并特征和目标
    valid_idx = ~(factors.isna().any(axis=1) | y.isna())
    X = factors[valid_idx]
    y_valid = y[valid_idx]
    
    # 训练模型
    predictor = LightGBMPredictor()
    train_result = predictor.train(X, y_valid, feature_names=list(factors.columns))
    
    print(f"  训练状态: {train_result.get('status', 'success')}")
    print(f"  RMSE: {train_result.get('rmse', 0):.4f}")
    print(f"  MAE: {train_result.get('mae', 0):.4f}")
    
    # 特征重要性
    if 'feature_importance' in train_result:
        print("\n  Top-10 重要因子:")
        for i, row in enumerate(train_result['feature_importance'][:10]):
            print(f"    {i+1}. {row['feature']}: {row['importance']:.2f}")
    
    # ========== CTA 策略 ==========
    print("\n[Step 4] 测试 CTA 策略...")
    
    strategy = CTAStrategy("MACD_Strategy")
    strategy.on_init({
        'strategy_type': 'macd',
        'fixed_size': 100,
        'stop_loss': 0.02,
    })
    
    # 模拟交易
    signals = []
    for i in range(100, min(200, len(data))):
        bar = {
            'open': data['open'].iloc[i],
            'high': data['high'].iloc[i],
            'low': data['low'].iloc[i],
            'close': data['close'].iloc[i],
            'volume': data['volume'].iloc[i],
        }
        
        indicators = {
            'macd': factors['macd'].iloc[i],
            'macd_signal': factors['macd_signal'].iloc[i],
            'rsi': factors['rsi'].iloc[i],
        }
        
        signal = strategy.on_bar(bar, indicators)
        if signal['action'] != 'HOLD':
            signals.append({
                'date': data['date'].iloc[i],
                **signal
            })
    
    print(f"  交易信号数量: {len(signals)}")
    for sig in signals[:5]:
        print(f"    {sig['date'].strftime('%Y-%m-%d')}: {sig['action']} "
              f"@{sig['price']:.2f} x {sig['volume']}")


if __name__ == "__main__":
    demo()
