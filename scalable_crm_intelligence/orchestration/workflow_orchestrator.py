"""
Workflow Orchestrator
Coordinates execution of multiple components in intelligent workflows
"""

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from core.base.component import BaseComponent, ComponentConfig

@dataclass
class WorkflowStep:
    """Represents a single step in a workflow"""
    component_name: str
    input_mapping: Dict[str, str]
    output_mapping: Dict[str, str]
    dependencies: List[str] = None
    optional: bool = False
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class WorkflowConfig:
    """Configuration for a workflow"""
    name: str
    description: str
    steps: List[WorkflowStep]
    parallel_execution: bool = False
    failure_strategy: str = "stop"  # stop, continue, retry

class WorkflowOrchestrator:
    """Orchestrates execution of component workflows"""
    
    def __init__(self):
        self.components = {}
        self.workflows = {}
        
    def register_component(self, name: str, component: BaseComponent):
        """Register a component for use in workflows"""
        self.components[name] = component
        
    def register_workflow(self, config: WorkflowConfig):
        """Register a workflow configuration"""
        self.workflows[config.name] = config
        
    async def execute_workflow(self, workflow_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a registered workflow"""
        
        if workflow_name not in self.workflows:
            raise ValueError(f"Workflow '{workflow_name}' not found")
            
        workflow = self.workflows[workflow_name]
        context = {"input": input_data, "steps": {}}
        
        if workflow.parallel_execution:
            return await self._execute_parallel(workflow, context)
        else:
            return await self._execute_sequential(workflow, context)
            
    async def _execute_sequential(self, workflow: WorkflowConfig, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow steps sequentially"""
        
        for step in workflow.steps:
            try:
                # Check dependencies
                if not self._check_dependencies(step, context):
                    if not step.optional:
                        raise RuntimeError(f"Dependencies not met for step: {step.component_name}")
                    continue
                    
                # Prepare input
                step_input = self._map_input(step, context)
                
                # Execute component
                component = self.components[step.component_name]
                result = await component.execute(step_input)
                
                # Store result
                context["steps"][step.component_name] = result
                
                # Map output to context
                self._map_output(step, result, context)
                
            except Exception as e:
                if workflow.failure_strategy == "stop":
                    raise
                elif workflow.failure_strategy == "continue":
                    context["steps"][step.component_name] = {"error": str(e)}
                    
        return context
        
    async def _execute_parallel(self, workflow: WorkflowConfig, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow steps in parallel where possible"""
        
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(workflow.steps)
        
        # Execute in topological order with parallelization
        executed = set()
        
        while len(executed) < len(workflow.steps):
            # Find steps ready to execute
            ready_steps = [
                step for step in workflow.steps 
                if step.component_name not in executed 
                and all(dep in executed for dep in step.dependencies)
            ]
            
            if not ready_steps:
                break
                
            # Execute ready steps in parallel
            tasks = []
            for step in ready_steps:
                step_input = self._map_input(step, context)
                component = self.components[step.component_name]
                task = asyncio.create_task(component.execute(step_input))
                tasks.append((step, task))
                
            # Wait for completion
            for step, task in tasks:
                try:
                    result = await task
                    context["steps"][step.component_name] = result
                    self._map_output(step, result, context)
                    executed.add(step.component_name)
                except Exception as e:
                    if workflow.failure_strategy == "stop":
                        raise
                    context["steps"][step.component_name] = {"error": str(e)}
                    executed.add(step.component_name)
                    
        return context
        
    def _check_dependencies(self, step: WorkflowStep, context: Dict[str, Any]) -> bool:
        """Check if step dependencies are satisfied"""
        return all(dep in context["steps"] for dep in step.dependencies)
        
    def _map_input(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Map context data to step input"""
        step_input = {}
        
        for input_key, context_path in step.input_mapping.items():
            value = self._get_nested_value(context, context_path)
            if value is not None:
                step_input[input_key] = value
                
        return step_input
        
    def _map_output(self, step: WorkflowStep, result: Dict[str, Any], context: Dict[str, Any]):
        """Map step output to context"""
        for context_path, output_key in step.output_mapping.items():
            if output_key in result:
                self._set_nested_value(context, context_path, result[output_key])
                
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
                
        return value
        
    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any):
        """Set value in nested dictionary using dot notation"""
        keys = path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
            
        current[keys[-1]] = value
        
    def _build_dependency_graph(self, steps: List[WorkflowStep]) -> Dict[str, List[str]]:
        """Build dependency graph for parallel execution"""
        graph = {}
        
        for step in steps:
            graph[step.component_name] = step.dependencies
            
        return graph
