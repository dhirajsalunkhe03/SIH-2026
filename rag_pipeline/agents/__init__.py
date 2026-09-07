#!/usr/bin/env python3
"""
Phase 6: Multi-Agent Architecture for Legal RAG.

Agents:
- Legal Agent: Acts, Sections, Rules, legal definitions, procedures
- TK Agent: Traditional Knowledge, community knowledge, TK protection
- ABS Agent: Access & Benefit Sharing, biological resources, biodiversity
- IP Agent: Patents, Trademarks, GI, Designs, Copyright, Plant Varieties

All agents share the existing RAG infrastructure (ChromaDB, retriever, Qwen3).
"""

from agents.base_agent import BaseAgent, AgentResult
from agents.legal_agent import LegalAgent
from agents.tk_agent import TKAgent
from agents.abs_agent import ABSAgent
from agents.ip_agent import IPAgent
from agents.orchestrator import Orchestrator, RoutingDecision

__all__ = [
    'BaseAgent',
    'AgentResult', 
    'LegalAgent',
    'TKAgent',
    'ABSAgent',
    'IPAgent',
    'Orchestrator',
    'RoutingDecision',
]