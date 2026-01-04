"""
BudgetMapper - 预算映射

将 TestSpec 的 Budget 映射到 AgentConfig 和 Policy。
"""

from doc2spec.models.testspec import TestSpec, Budget
from t2p.models.task_bundle import AgentConfig, RetryConfig, RetryStrategy


class BudgetMapper:
    """预算映射器"""
    
    def __init__(self, lang: str = "cn"):
        self.lang = lang
    
    def map(self, budget: Budget) -> tuple[AgentConfig, RetryConfig, int]:
        """
        映射 Budget 到 AgentConfig 和 RetryConfig
        
        Args:
            budget: TestSpec 的 Budget
            
        Returns:
            tuple: (AgentConfig, RetryConfig, timeout_sec)
        """
        # 映射到 AgentConfig
        agent_config = AgentConfig(
            max_steps=budget.max_steps,
            lang=self.lang,
        )
        
        # 映射到 RetryConfig
        retry_config = RetryConfig(
            max_attempts=budget.retries.max_attempts,
            backoff_sec=budget.retries.backoff_sec,
            strategy=RetryStrategy.BACKOFF if budget.retries.backoff_sec > 0 else RetryStrategy.IMMEDIATE
        )
        
        return agent_config, retry_config, budget.timeout_sec
    
    def map_from_spec(self, spec: TestSpec) -> tuple[AgentConfig, RetryConfig, int]:
        """从完整 TestSpec 映射"""
        return self.map(spec.budget)
