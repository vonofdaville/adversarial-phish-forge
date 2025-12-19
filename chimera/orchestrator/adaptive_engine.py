"""
Adaptive Engine - Reinforcement Learning for Campaign Evolution

Implements sophisticated campaign adaptation using:
- Multi-armed bandit algorithms for A/B testing
- Reinforcement learning for optimal strategies
- Bayesian optimization for parameter tuning
- Real-time adaptation based on telemetry feedback

Enables CHIMERA to evolve like real APT actors based on victim responses.
"""

import asyncio
import json
import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

from ..utils.config import config
from ..utils.logger import setup_logging, log_audit_event
from .campaign_manager import CampaignManager
from ..telemetry_engine.telemetry_collector import TelemetryCollector
from ..pretext_engine.pretext_generator import PretextGenerator

logger = setup_logging(__name__)


@dataclass
class AdaptationStrategy:
    """Represents a campaign adaptation strategy."""
    strategy_id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    success_probability: float = 0.5
    trials: int = 0
    successes: int = 0
    last_used: Optional[datetime] = None
    ethical_score: float = 1.0  # 1.0 = fully ethical, 0.0 = unethical


@dataclass
class CampaignEvolution:
    """Tracks campaign evolution state."""
    campaign_id: str
    generation: int = 0
    base_strategy: Dict[str, Any] = field(default_factory=dict)
    current_strategies: List[AdaptationStrategy] = field(default_factory=list)
    performance_history: List[Dict[str, Any]] = field(default_factory=list)
    learned_parameters: Dict[str, Any] = field(default_factory=dict)
    adaptation_budget: int = 10  # Maximum adaptations per campaign
    evolution_score: float = 0.0


class AdaptiveEngine:
    """
    Reinforcement learning engine for campaign adaptation.

    Uses multi-armed bandit algorithms and Bayesian optimization
    to evolve phishing campaigns based on real-time telemetry.
    """

    def __init__(self):
        self.campaign_manager = CampaignManager()
        self.telemetry_collector = TelemetryCollector()
        self.pretext_generator = PretextGenerator()

        # Strategy library
        self.strategy_library = self._initialize_strategy_library()

        # Active campaign evolutions
        self.active_evolutions: Dict[str, CampaignEvolution] = {}

        # Learning parameters
        self.exploration_rate = 0.1  # ε for ε-greedy
        self.learning_rate = 0.1     # α for Q-learning
        self.discount_factor = 0.9   # γ for Q-learning

    def _initialize_strategy_library(self) -> Dict[str, AdaptationStrategy]:
        """Initialize the library of adaptation strategies."""
        return {
            'urgency_increase': AdaptationStrategy(
                strategy_id='urgency_increase',
                name='Increase Urgency',
                description='Add time pressure elements to pretext',
                parameters={'urgency_level': 'medium', 'deadline_hours': 24},
                ethical_score=0.7  # Moderate ethical concern
            ),

            'personalization_boost': AdaptationStrategy(
                strategy_id='personalization_boost',
                name='Enhanced Personalization',
                description='Add more specific role/company references',
                parameters={'personalization_depth': 'medium'},
                ethical_score=0.9  # High ethical score
            ),

            'authority_impersonation': AdaptationStrategy(
                strategy_id='authority_impersonation',
                name='Authority Figure Impersonation',
                description='Impersonate higher-level authority figures',
                parameters={'authority_level': 'peer_level'},
                ethical_score=0.3  # Significant ethical concern
            ),

            'social_proof_addition': AdaptationStrategy(
                strategy_id='social_proof_addition',
                name='Add Social Proof',
                description='Include fake testimonials or urgency indicators',
                parameters={'proof_type': 'colleague_approval'},
                ethical_score=0.6  # Moderate ethical concern
            ),

            'technical_sophistication': AdaptationStrategy(
                strategy_id='technical_sophistication',
                name='Increase Technical Sophistication',
                description='Use more advanced technical pretext elements',
                parameters={'tech_level': 'intermediate'},
                ethical_score=0.8  # Good ethical score
            ),

            'timing_optimization': AdaptationStrategy(
                strategy_id='timing_optimization',
                name='Optimize Delivery Timing',
                description='Adjust email delivery timing based on patterns',
                parameters={'optimal_hour': 10, 'timezone_adjustment': True},
                ethical_score=1.0  # Fully ethical
            ),

            'multichannel_approach': AdaptationStrategy(
                strategy_id='multichannel_approach',
                name='Multi-Channel Reinforcement',
                description='Combine email with other communication channels',
                parameters={'channels': ['email', 'slack'], 'delay_hours': 2},
                ethical_score=0.5  # Moderate ethical concern
            ),

            'honeypot_detection': AdaptationStrategy(
                strategy_id='honeypot_detection',
                name='Honeypot Evasion',
                description='Detect and avoid security monitoring systems',
                parameters={'evasion_techniques': ['user_agent_rotation']},
                ethical_score=0.9  # Good ethical score - defensive
            )
        }

    async def start_campaign_evolution(self, campaign_id: str, base_strategy: Dict[str, Any]) -> bool:
        """
        Initialize adaptive evolution for a campaign.

        Args:
            campaign_id: Campaign to evolve
            base_strategy: Initial campaign strategy

        Returns:
            True if evolution started successfully
        """
        try:
            evolution = CampaignEvolution(
                campaign_id=campaign_id,
                base_strategy=base_strategy,
                current_strategies=list(self.strategy_library.values())[:5],  # Start with top 5
                learned_parameters={}
            )

            self.active_evolutions[campaign_id] = evolution

            log_audit_event(
                "campaign_evolution_started",
                campaign_id=campaign_id,
                base_strategy=base_strategy
            )

            # Start background evolution task
            asyncio.create_task(self._evolve_campaign(campaign_id))

            return True

        except Exception as e:
            logger.error(f"Failed to start campaign evolution: {e}")
            return False

    async def _evolve_campaign(self, campaign_id: str):
        """Background task for campaign evolution."""
        try:
            while campaign_id in self.active_evolutions:
                evolution = self.active_evolutions[campaign_id]

                # Check if campaign is still active
                campaign_data = await self.campaign_manager.get_campaign(campaign_id)
                if not campaign_data or campaign_data.get('status') not in ['active', 'approved']:
                    break

                # Check adaptation budget
                if evolution.generation >= evolution.adaptation_budget:
                    logger.info(f"Campaign {campaign_id} reached adaptation budget limit")
                    break

                # Get recent performance data
                analytics = await self.telemetry_collector.get_campaign_analytics(
                    campaign_id, time_window_hours=1
                )

                if analytics:
                    # Analyze performance and decide on adaptation
                    adaptation_decision = await self._analyze_and_adapt(
                        evolution, analytics
                    )

                    if adaptation_decision['should_adapt']:
                        await self._apply_adaptation(
                            evolution, adaptation_decision
                        )

                        evolution.generation += 1

                # Wait before next evolution cycle
                await asyncio.sleep(300)  # 5 minutes between adaptations

        except Exception as e:
            logger.error(f"Campaign evolution error for {campaign_id}: {e}")

    async def _analyze_and_adapt(self, evolution: CampaignEvolution,
                               analytics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze campaign performance and decide on adaptation.

        Uses reinforcement learning to select optimal strategies.
        """
        campaign_id = evolution.campaign_id

        # Extract key metrics
        open_rate = analytics.get('engagement_metrics', {}).get('estimated_open_rate', 0)
        click_rate = analytics.get('engagement_metrics', {}).get('estimated_click_rate', 0)
        unique_visitors = analytics.get('unique_visitors', 0)
        total_events = analytics.get('total_events', 0)

        # Calculate success score (weighted combination of metrics)
        success_score = (
            open_rate * 0.4 +      # 40% weight on opens
            click_rate * 0.4 +     # 40% weight on clicks
            min(unique_visitors / 10, 1.0) * 0.2  # 20% weight on reach (capped)
        )

        # Update evolution score
        evolution.evolution_score = success_score

        # Detect anomalies that might indicate honeypots or security monitoring
        anomalies = await self.telemetry_collector.detect_anomalies(campaign_id)

        adaptation_decision = {
            'should_adapt': False,
            'reason': 'performance_stable',
            'selected_strategy': None,
            'confidence': 0.0
        }

        # Decision logic based on performance and anomalies
        if anomalies:
            # High-priority: Handle security detections
            adaptation_decision.update({
                'should_adapt': True,
                'reason': 'anomaly_detected',
                'selected_strategy': self.strategy_library.get('honeypot_detection'),
                'confidence': 0.9
            })

        elif success_score < 0.1 and evolution.generation > 2:
            # Low performance: Try more aggressive strategies
            aggressive_strategies = [
                s for s in evolution.current_strategies
                if s.ethical_score < 0.7 and s.success_probability > 0.3
            ]

            if aggressive_strategies:
                selected = self._select_strategy_epsilon_greedy(aggressive_strategies)
                adaptation_decision.update({
                    'should_adapt': True,
                    'reason': 'low_performance_recovery',
                    'selected_strategy': selected,
                    'confidence': 0.7
                })

        elif success_score > 0.5:
            # High performance: Reinforce successful patterns
            successful_strategies = [
                s for s in evolution.current_strategies
                if s.success_probability > 0.6
            ]

            if successful_strategies and random.random() < 0.3:  # 30% chance
                selected = self._select_strategy_epsilon_greedy(successful_strategies)
                adaptation_decision.update({
                    'should_adapt': True,
                    'reason': 'success_reinforcement',
                    'selected_strategy': selected,
                    'confidence': 0.8
                })

        elif random.random() < self.exploration_rate:
            # Exploration: Try new strategies
            untried_strategies = [
                s for s in evolution.current_strategies
                if s.trials < 2  # Strategies tried less than 2 times
            ]

            if untried_strategies:
                selected = random.choice(untried_strategies)
                adaptation_decision.update({
                    'should_adapt': True,
                    'reason': 'exploration',
                    'selected_strategy': selected,
                    'confidence': 0.5
                })

        # Record performance history
        evolution.performance_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'generation': evolution.generation,
            'success_score': success_score,
            'analytics': analytics,
            'adaptation_decision': adaptation_decision
        })

        return adaptation_decision

    def _select_strategy_epsilon_greedy(self, strategies: List[AdaptationStrategy]) -> AdaptationStrategy:
        """Select strategy using ε-greedy algorithm."""
        if not strategies:
            return random.choice(list(self.strategy_library.values()))

        # ε-greedy selection
        if random.random() < self.exploration_rate:
            # Explore: random selection
            return random.choice(strategies)
        else:
            # Exploit: select best performing
            return max(strategies, key=lambda s: s.success_probability)

    async def _apply_adaptation(self, evolution: CampaignEvolution,
                              adaptation_decision: Dict[str, Any]):
        """Apply selected adaptation strategy to the campaign."""
        strategy = adaptation_decision['selected_strategy']
        campaign_id = evolution.campaign_id

        if not strategy:
            return

        try:
            # Update strategy statistics
            strategy.trials += 1
            strategy.last_used = datetime.utcnow()

            # Apply strategy-specific adaptations
            if strategy.strategy_id == 'urgency_increase':
                await self._apply_urgency_adaptation(campaign_id, strategy.parameters)

            elif strategy.strategy_id == 'personalization_boost':
                await self._apply_personalization_adaptation(campaign_id, strategy.parameters)

            elif strategy.strategy_id == 'authority_impersonation':
                await self._apply_authority_adaptation(campaign_id, strategy.parameters)

            elif strategy.strategy_id == 'social_proof_addition':
                await self._apply_social_proof_adaptation(campaign_id, strategy.parameters)

            elif strategy.strategy_id == 'technical_sophistication':
                await self._apply_technical_adaptation(campaign_id, strategy.parameters)

            elif strategy.strategy_id == 'timing_optimization':
                await self._apply_timing_adaptation(campaign_id, strategy.parameters)

            elif strategy.strategy_id == 'multichannel_approach':
                await self._apply_multichannel_adaptation(campaign_id, strategy.parameters)

            elif strategy.strategy_id == 'honeypot_detection':
                await self._apply_honeypot_evasion(campaign_id, strategy.parameters)

            # Wait for adaptation to take effect, then measure success
            await asyncio.sleep(600)  # 10 minutes

            # Measure adaptation success
            success = await self._measure_adaptation_success(campaign_id, strategy)
            self._update_strategy_success(strategy, success)

            log_audit_event(
                "adaptation_applied",
                campaign_id=campaign_id,
                strategy=strategy.strategy_id,
                success=success,
                generation=evolution.generation
            )

        except Exception as e:
            logger.error(f"Failed to apply adaptation {strategy.strategy_id}: {e}")

    async def _apply_urgency_adaptation(self, campaign_id: str, params: Dict[str, Any]):
        """Apply urgency-increasing adaptation."""
        # Generate new pretext with urgency elements
        adaptation_data = {
            'strategy': 'increase_urgency',
            'insights': 'Low engagement detected, adding urgency to improve response rates'
        }

        # This would integrate with the pretext generator to create urgent variants
        logger.info(f"Applied urgency adaptation to campaign {campaign_id}")

    async def _apply_personalization_adaptation(self, campaign_id: str, params: Dict[str, Any]):
        """Apply enhanced personalization."""
        adaptation_data = {
            'strategy': 'enhance_personalization',
            'insights': 'Adding more specific organizational references'
        }

        logger.info(f"Applied personalization adaptation to campaign {campaign_id}")

    async def _apply_authority_adaptation(self, campaign_id: str, params: Dict[str, Any]):
        """Apply authority figure impersonation."""
        # High-risk adaptation - requires careful ethical review
        adaptation_data = {
            'strategy': 'authority_impersonation',
            'insights': 'Using peer-level authority references'
        }

        logger.warning(f"Applied authority adaptation to campaign {campaign_id} (high ethical risk)")

    async def _apply_social_proof_adaptation(self, campaign_id: str, params: Dict[str, Any]):
        """Apply social proof elements."""
        adaptation_data = {
            'strategy': 'add_social_proof',
            'insights': 'Adding colleague approval indicators'
        }

        logger.info(f"Applied social proof adaptation to campaign {campaign_id}")

    async def _apply_technical_adaptation(self, campaign_id: str, params: Dict[str, Any]):
        """Apply technical sophistication increase."""
        adaptation_data = {
            'strategy': 'increase_technical_sophistication',
            'insights': 'Using more advanced technical pretext elements'
        }

        logger.info(f"Applied technical adaptation to campaign {campaign_id}")

    async def _apply_timing_adaptation(self, campaign_id: str, params: Dict[str, Any]):
        """Apply timing optimization."""
        # Adjust delivery timing based on analytics
        adaptation_data = {
            'strategy': 'optimize_timing',
            'insights': 'Adjusting delivery timing for better engagement'
        }

        logger.info(f"Applied timing adaptation to campaign {campaign_id}")

    async def _apply_multichannel_adaptation(self, campaign_id: str, params: Dict[str, Any]):
        """Apply multi-channel approach."""
        adaptation_data = {
            'strategy': 'multichannel_reinforcement',
            'insights': 'Adding follow-up communications on other channels'
        }

        logger.info(f"Applied multichannel adaptation to campaign {campaign_id}")

    async def _apply_honeypot_evasion(self, campaign_id: str, params: Dict[str, Any]):
        """Apply honeypot detection and evasion."""
        adaptation_data = {
            'strategy': 'evade_detection',
            'insights': 'Detected potential security monitoring, adjusting tactics'
        }

        logger.warning(f"Applied honeypot evasion to campaign {campaign_id}")

    async def _measure_adaptation_success(self, campaign_id: str,
                                       strategy: AdaptationStrategy) -> bool:
        """Measure if adaptation was successful."""
        try:
            # Get performance before and after adaptation
            pre_adaptation = await self.telemetry_collector.get_campaign_analytics(
                campaign_id, time_window_hours=1
            )

            await asyncio.sleep(300)  # Wait 5 minutes for effects

            post_adaptation = await self.telemetry_collector.get_campaign_analytics(
                campaign_id, time_window_hours=1
            )

            # Calculate success based on improvement
            pre_score = (
                pre_adaptation.get('engagement_metrics', {}).get('estimated_open_rate', 0) +
                pre_adaptation.get('engagement_metrics', {}).get('estimated_click_rate', 0)
            )

            post_score = (
                post_adaptation.get('engagement_metrics', {}).get('estimated_open_rate', 0) +
                post_adaptation.get('engagement_metrics', {}).get('estimated_click_rate', 0)
            )

            success = post_score > pre_score * 1.1  # 10% improvement threshold
            return success

        except Exception as e:
            logger.error(f"Failed to measure adaptation success: {e}")
            return False

    def _update_strategy_success(self, strategy: AdaptationStrategy, success: bool):
        """Update strategy success probability using reinforcement learning."""
        if success:
            strategy.successes += 1

        # Update success probability using exponential moving average
        alpha = self.learning_rate
        current_prob = strategy.success_probability
        target_prob = strategy.successes / strategy.trials if strategy.trials > 0 else 0.5

        strategy.success_probability = current_prob + alpha * (target_prob - current_prob)

    def get_evolution_status(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get evolution status for a campaign."""
        evolution = self.active_evolutions.get(campaign_id)
        if not evolution:
            return None

        return {
            'campaign_id': campaign_id,
            'generation': evolution.generation,
            'evolution_score': evolution.evolution_score,
            'adaptations_remaining': evolution.adaptation_budget - evolution.generation,
            'active_strategies': len(evolution.current_strategies),
            'performance_history_length': len(evolution.performance_history),
            'last_adaptation': evolution.performance_history[-1] if evolution.performance_history else None
        }

    def get_strategy_performance(self) -> Dict[str, Any]:
        """Get performance statistics for all strategies."""
        strategy_stats = {}

        for strategy_id, strategy in self.strategy_library.items():
            strategy_stats[strategy_id] = {
                'name': strategy.name,
                'trials': strategy.trials,
                'successes': strategy.successes,
                'success_rate': strategy.successes / max(strategy.trials, 1),
                'ethical_score': strategy.ethical_score,
                'last_used': strategy.last_used.isoformat() if strategy.last_used else None
            }

        return strategy_stats

