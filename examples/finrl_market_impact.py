#!/usr/bin/env python3
"""
FinRL Market Impact 环境示例
基于 FinRL v1.x + FinRL-X 的强化学习交易框架

核心特性：
1. 四层架构 (Data -> Env -> Agent -> Zoo)
2. Market Impact 环境
3. 统一权重语义
4. 多券商集成
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import gymnasium as gym
from gymnasium import spaces


class TradingAction(Enum):
    """交易动作"""
    HOLD = 0
    BUY = 1
    SELL = 2


@dataclass
class TradeOrder:
    """交易订单"""
    stock_code: str
    action: TradingAction
    quantity: int
    price: float
    timestamp: datetime
    market_impact: float = 0.0
    commission: float = 0.0


@dataclass
class PortfolioState:
    """投资组合状态"""
    cash: float
    positions: Dict[str, int]  # stock_code -> shares
    position_value: float
    total_value: float
    daily_return: float


class MarketImpactEnv(gym.Env):
    """
    市场冲击环境
    
    特点:
    1. 集成交易成本模型 (AC/OW/Sqrt)
    2. 支持订单薄模拟
    3. 多资产支持
    """
    
    metadata = {'render_modes': ['human']}
    
    def __init__(
        self,
        price_data: pd.DataFrame,
        initial_balance: float = 1000000,
        transaction_cost_pct: float = 0.001,
        market_impact_model: str = "sqrt",
        max_position: float = 0.3,
        num_stocks: int = 1,
    ):
        super().__init__()
        
        self.price_data = price_data
        self.initial_balance = initial_balance
        self.transaction_cost_pct = transaction_cost_pct
        self.market_impact_model = market_impact_model
        self.max_position = max_position
        self.num_stocks = num_stocks
        
        # 数据索引
        self.current_step = 0
        self.max_steps = len(price_data)
        
        # 动作空间: 买入/持有/卖出 (-1, 0, 1)
        self.action_space = spaces.Box(
            low=-1, high=1, shape=(num_stocks,), dtype=np.float32
        )
        
        # 观察空间
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(num_stocks * 6 + 1,),  # price, ma5, ma20, volume, position, cash
            dtype=np.float32
        )
        
        # 账户状态
        self.cash = initial_balance
        self.positions = {f"stock_{i}": 0 for i in range(num_stocks)}
        self.initial_value = initial_balance
        
        # 交易历史
        self.trade_history: List[TradeOrder] = []
    
    def _get_observation(self) -> np.ndarray:
        """获取观察"""
        obs = []
        
        for i in range(self.num_stocks):
            stock_id = f"stock_{i}"
            stock_data = self.price_data[self.price_data['stock_id'] == stock_id].iloc[self.current_step]
            
            obs.extend([
                stock_data['close'] / stock_data.get('close_ma5', stock_data['close']) - 1,
                stock_data['close'] / stock_data.get('close_ma20', stock_data['close']) - 1,
                stock_data.get('volume_ratio', 1.0),
                self.positions[stock_id] * stock_data['close'] / self.cash,
                self.cash / self.initial_balance,
            ])
        
        obs.append(self.current_step / self.max_steps)  # 时间进度
        return np.array(obs, dtype=np.float32)
    
    def _calculate_market_impact(
        self, 
        order_quantity: int, 
        daily_volume: float,
        volatility: float
    ) -> float:
        """计算市场冲击"""
        if daily_volume <= 0:
            return 0.0
        
        participation = abs(order_quantity) / daily_volume
        
        if self.market_impact_model == "sqrt":
            # 平方根模型
            return 0.5 * volatility * np.sqrt(participation)
        elif self.market_impact_model == "ac":
            # Almgren-Chriss
            return 0.1 * participation + 0.1 * np.sqrt(participation) * volatility
        else:
            # 线性模型
            return 0.1 * participation
    
    def _execute_trade(
        self,
        stock_id: str,
        action: float,
        current_price: float,
        daily_volume: float,
        volatility: float
    ) -> Tuple[float, float]:
        """
        执行交易
        
        Returns:
            (realized_return, total_cost)
        """
        # 计算订单数量
        position_value = self.positions[stock_id] * current_price
        target_position = action * self.cash * self.max_position
        
        order_quantity = int((target_position - position_value) / current_price)
        
        if order_quantity == 0:
            return 0.0, 0.0
        
        # 计算成本
        market_impact = self._calculate_market_impact(
            order_quantity, daily_volume, volatility
        )
        commission = abs(order_quantity * current_price * self.transaction_cost_pct)
        slippage = abs(order_quantity * current_price * 0.0002)  # 0.2bp滑点
        
        total_cost = (market_impact + slippage) * abs(order_quantity) + commission
        
        # 更新仓位
        if order_quantity > 0:  # 买入
            cost = order_quantity * current_price + total_cost
            if cost <= self.cash:
                self.positions[stock_id] += order_quantity
                self.cash -= cost
        else:  # 卖出
            sell_quantity = min(abs(order_quantity), self.positions[stock_id])
            if sell_quantity > 0:
                self.positions[stock_id] -= sell_quantity
                self.cash += sell_quantity * current_price - total_cost
        
        return total_cost, market_impact
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """执行一步"""
        # 解析动作
        actions = action[:self.num_stocks]
        
        total_cost = 0.0
        total_market_impact = 0.0
        
        # 执行交易
        for i, act in enumerate(actions):
            stock_id = f"stock_{i}"
            stock_data = self.price_data[self.price_data['stock_id'] == stock_id].iloc[self.current_step]
            
            cost, impact = self._execute_trade(
                stock_id,
                float(act),
                stock_data['close'],
                stock_data.get('volume', 1e6),
                stock_data.get('volatility', 0.02)
            )
            total_cost += cost
            total_market_impact += impact
        
        # 计算收益
        prev_total_value = self._get_portfolio_value()
        
        self.current_step += 1
        
        if self.current_step >= self.max_steps - 1:
            terminated = True
        else:
            terminated = False
        
        # 获取新状态
        obs = self._get_observation()
        curr_total_value = self._get_portfolio_value()
        
        # 计算奖励 (对数收益率 - 交易成本)
        reward = np.log(curr_total_value / prev_total_value) if prev_total_value > 0 else 0
        reward -= total_cost / curr_total_value if curr_total_value > 0 else 0
        
        truncated = False
        info = {
            'portfolio_value': curr_total_value,
            'total_cost': total_cost,
            'market_impact': total_market_impact,
            'return': (curr_total_value - self.initial_balance) / self.initial_balance,
        }
        
        return obs, reward, terminated, truncated, info
    
    def _get_portfolio_value(self) -> float:
        """计算组合价值"""
        position_value = sum(
            self.positions[s] * self.price_data[
                self.price_data['stock_id'] == s
            ].iloc[min(self.current_step, len(self.price_data)-1)]['close']
            for s in self.positions
        )
        return self.cash + position_value
    
    def reset(self, seed: Optional[int] = None) -> Tuple[np.ndarray, Dict]:
        """重置环境"""
        super().reset(seed=seed)
        
        self.current_step = 0
        self.cash = self.initial_balance
        self.positions = {f"stock_{i}": 0 for i in range(self.num_stocks)}
        self.trade_history = []
        
        return self._get_observation(), {}


class UnifiedWeightSystem:
    """
    统一权重语义
    
    FinRL-X 的核心创新：统一管理多智能体权重
    """
    
    def __init__(self):
        self.agent_weights: Dict[str, float] = {}
        self.history: List[Dict] = []
    
    def update_weights(
        self,
        agent_id: str,
        performance: float,
        risk_contribution: float,
        lr: float = 0.01
    ):
        """
        更新智能体权重
        
        Args:
            agent_id: 智能体ID
            performance: 性能指标 (0-1)
            risk_contribution: 风险贡献 (0-1)
            lr: 学习率
        """
        # 基于性能和风险调整权重
        target_weight = performance * (1 - risk_contribution * 0.5)
        
        current_weight = self.agent_weights.get(agent_id, 0.1)
        new_weight = current_weight + lr * (target_weight - current_weight)
        
        self.agent_weights[agent_id] = max(0.01, min(1.0, new_weight))
        
        self.history.append({
            "agent_id": agent_id,
            "performance": performance,
            "risk_contribution": risk_contribution,
            "weight": new_weight,
            "timestamp": datetime.now(),
        })
    
    def get_weighted_action(
        self,
        actions: Dict[str, np.ndarray]
    ) -> np.ndarray:
        """获取加权动作"""
        weighted_action = np.zeros_like(list(actions.values())[0])
        total_weight = 0
        
        for agent_id, action in actions.items():
            weight = self.agent_weights.get(agent_id, 0.1)
            weighted_action += weight * action
            total_weight += weight
        
        if total_weight > 0:
            weighted_action /= total_weight
        
        return weighted_action
    
    def normalize_weights(self) -> Dict[str, float]:
        """归一化权重"""
        total = sum(self.agent_weights.values())
        if total > 0:
            return {k: v/total for k, v in self.agent_weights.items()}
        return self.agent_weights


class FinRLAgent:
    """
    FinRL 智能体基类
    
    支持算法:
    - PPO
    - A2C
    - DDPG
    - TD3
    """
    
    def __init__(
        self,
        env,
        algo: str = "ppo",
        model_params: Optional[Dict] = None
    ):
        self.env = env
        self.algo = algo
        self.model_params = model_params or {}
        self.model = None
        self.training_log: List[Dict] = []
    
    def train(
        self,
        total_timesteps: int,
        callback=None,
        verbose: int = 1
    ) -> Dict:
        """训练智能体"""
        from stable_baselines3 import PPO, A2C, DDPG
        
        if self.model is None:
            if self.algo.lower() == "ppo":
                self.model = PPO(
                    "MlpPolicy",
                    self.env,
                    verbose=verbose,
                    **self.model_params
                )
            elif self.algo.lower() == "a2c":
                self.model = A2C(
                    "MlpPolicy",
                    self.env,
                    verbose=verbose,
                    **self.model_params
                )
            elif self.algo.lower() == "ddpg":
                self.model = DDPG(
                    "MlpPolicy",
                    self.env,
                    verbose=verbose,
                    **self.model_params
                )
        
        self.model.learn(
            total_timesteps=total_timesteps,
            callback=callback,
            progress_bar=verbose > 0
        )
        
        return {"status": "trained"}
    
    def predict(self, obs: np.ndarray) -> np.ndarray:
        """预测动作"""
        if self.model is None:
            raise ValueError("Model not trained yet")
        action, _ = self.model.predict(obs)
        return action
    
    def save(self, path: str):
        """保存模型"""
        if self.model:
            self.model.save(path)
    
    def load(self, path: str):
        """加载模型"""
        from stable_baselines3 import PPO, A2C, DDPG
        
        algos = {"ppo": PPO, "a2c": A2C, "ddpg": DDPG}
        self.model = algos[self.algo].load(path)


def create_sample_data(
    num_days: int = 252,
    num_stocks: int = 1
) -> pd.DataFrame:
    """创建示例数据"""
    np.random.seed(42)
    
    data = []
    base_price = 100
    
    for stock_id in range(num_stocks):
        prices = [base_price + stock_id * 50]
        
        for day in range(num_days):
            # 几何布朗运动
            drift = 0.0003
            volatility = 0.02
            
            price_change = prices[-1] * (
                drift + volatility * np.random.randn()
            )
            new_price = max(10, prices[-1] + price_change)
            prices.append(new_price)
            
            # 技术指标
            ma5 = np.mean(prices[-5:])
            ma20 = np.mean(prices[-20:]) if len(prices) >= 20 else new_price
            
            data.append({
                'date': datetime(2025, 1, 1) + timedelta(days=day),
                'stock_id': f"stock_{stock_id}",
                'open': new_price * (1 + np.random.uniform(-0.01, 0.01)),
                'high': new_price * (1 + np.random.uniform(0, 0.02)),
                'low': new_price * (1 - np.random.uniform(0, 0.02)),
                'close': new_price,
                'volume': np.random.uniform(1e6, 5e6),
                'volume_ratio': np.random.uniform(0.5, 1.5),
                'close_ma5': ma5,
                'close_ma20': ma20,
                'volatility': volatility,
            })
    
    return pd.DataFrame(data)


def demo():
    """演示 FinRL Market Impact 环境"""
    
    print("\n" + "="*70)
    print("  FinRL Market Impact 环境演示")
    print("="*70)
    
    # 创建示例数据
    print("\n[Step 1] 准备市场数据...")
    data = create_sample_data(num_days=100, num_stocks=1)
    print(f"  数据量: {len(data)} 条")
    
    # 创建环境
    print("\n[Step 2] 创建 Market Impact 环境...")
    env = MarketImpactEnv(
        price_data=data,
        initial_balance=1000000,
        transaction_cost_pct=0.001,
        market_impact_model="sqrt",
        max_position=0.3,
    )
    print(f"  动作空间: {env.action_space}")
    print(f"  观察空间: {env.observation_space}")
    
    # 测试环境
    print("\n[Step 3] 测试环境交互...")
    obs, info = env.reset()
    print(f"  初始现金: {env.cash:,.2f}")
    print(f"  初始观察维度: {len(obs)}")
    
    # 模拟交易
    for step in range(5):
        action = np.array([np.random.uniform(-0.5, 0.5)])  # 随机动作
        obs, reward, terminated, truncated, info = env.step(action)
        print(f"  Step {step+1}: 奖励={reward:.4f}, "
              f"成本={info['market_impact']:.4f}, "
              f"组合价值={info['portfolio_value']:,.0f}")
        
        if terminated:
            break
    
    # 统一权重系统测试
    print("\n[Step 4] 测试统一权重系统...")
    weight_system = UnifiedWeightSystem()
    
    agents = ["ppo_agent", "a2c_agent", "ddpg_agent"]
    for agent in agents:
        perf = np.random.uniform(0.3, 0.8)
        risk = np.random.uniform(0.1, 0.5)
        weight_system.update_weights(agent, perf, risk)
    
    weights = weight_system.normalize_weights()
    print("  归一化权重:")
    for agent, weight in weights.items():
        print(f"    {agent}: {weight:.4f}")
    
    # 加权动作
    actions = {
        "ppo_agent": np.array([0.5]),
        "a2c_agent": np.array([0.3]),
        "ddpg_agent": np.array([0.7]),
    }
    weighted = weight_system.get_weighted_action(actions)
    print(f"  加权动作: {weighted}")


if __name__ == "__main__":
    demo()
