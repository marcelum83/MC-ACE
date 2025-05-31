from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List

@dataclass
class Message:
    source_layer: str
    payload: Dict[str, Any] = field(default_factory=dict)

class NorthboundBus:
    def __init__(self):
        self._messages: Deque[Message] = deque()

    def publish(self, message: Message):
        self._messages.append(message)

    def get_messages(self) -> List[Message]:
        messages = list(self._messages)
        self._messages.clear()
        return messages

class SouthboundBus:
    def __init__(self):
        self._messages: Deque[Message] = deque()

    def publish(self, message: Message):
        self._messages.append(message)

    def get_messages(self) -> List[Message]:
        messages = list(self._messages)
        self._messages.clear()
        return messages

class ACELayer(ABC):
    def __init__(self, northbound_bus: NorthboundBus, southbound_bus: SouthboundBus, layer_name: str):
        self.northbound_bus = northbound_bus
        self.southbound_bus = southbound_bus
        self.layer_name = layer_name

    @abstractmethod
    def process_northbound(self, messages: List[Message]):
        pass

    @abstractmethod
    def process_southbound(self, messages: List[Message]):
        pass

    def send_northbound(self, payload: Dict[str, Any]):
        message = Message(source_layer=self.layer_name, payload=payload)
        self.northbound_bus.publish(message)

    def send_southbound(self, payload: Dict[str, Any]):
        message = Message(source_layer=self.layer_name, payload=payload)
        self.southbound_bus.publish(message)

class AspirationalLayer(ACELayer):
    def __init__(self, northbound_bus: NorthboundBus, southbound_bus: SouthboundBus, layer_name: str = "AspirationalLayer"):
        super().__init__(northbound_bus, southbound_bus, layer_name)
        self.constitution = {
            "Mission": "To be a helpful and friendly chat companion.",
            "Heuristic Imperatives": [
                "Be truthful and harmless.",
                "Engage in positive interactions.",
                "Learn from conversations to improve helpfulness."
            ],
            "Universal Declaration of Human Rights": "Adherence to UDHR principles, respecting dignity and rights."
        }
        # Send initial goals based on constitution
        self.send_southbound({"goal": "Establish friendly communication based on constitution."})

    def process_northbound(self, messages: List[Message]):
        print(f"[{self.layer_name}] Received northbound messages: {messages}")
        # Example: if a lower layer indicates user confusion, set a goal to clarify.
        for msg in messages:
            if msg.payload.get("status") == "user_confused":
                new_goal = "Increase understanding and clarify user's query."
                print(f"[{self.layer_name}] Setting new goal: {new_goal}")
                self.send_southbound({"goal": new_goal, "original_message_payload": msg.payload})
            # For now, let's assume any other northbound message is a general prompt for guidance
            elif msg.payload.get("action") == "request_guidance":
                 # Based on the constitution, decide on an overarching goal.
                 # This is a simplified example.
                constitutional_goal = "Reaffirm commitment to helpful and positive interaction."
                print(f"[{self.layer_name}] Sending constitutional guidance: {constitutional_goal}")
                self.send_southbound({"goal": constitutional_goal, "based_on_mission": self.constitution["Mission"]})


    def process_southbound(self, messages: List[Message]):
        # This layer is the highest, so it primarily sends messages south.
        # It might receive acknowledgements or status updates from Layer 2.
        print(f"[{self.layer_name}] Received southbound messages (e.g., acks, status, requests from L2): {messages}")
        for msg in messages:
            if msg.payload.get("status") == "acknowledged":
                print(f"[{self.layer_name}] Goal '{msg.payload.get('acknowledged_goal')}' acknowledged by {msg.source_layer}.")
            elif msg.payload.get("action") == "request_guidance":
                # This is a request from L2 (Strategy) for guidance.
                # L1 consults its constitution and sends goals southbound to L2.
                user_message_context = msg.payload.get("user_message", "") # Get user message for context
                print(f"[{self.layer_name}] Received guidance request from L2 regarding: '{user_message_context}'")

                # Example: Simple constitutional goal, could be more dynamic
                constitutional_goal = "Reaffirm commitment to helpful and positive interaction, considering user's message."
                if "confused" in user_message_context.lower() or "help" in user_message_context.lower():
                    constitutional_goal = "Increase understanding and clarify user's query effectively and kindly."

                print(f"[{self.layer_name}] Sending constitutional guidance to L2: {constitutional_goal}")
                # Pass original L2 message payload for context, L2 might need user_message from it
                self.send_southbound({
                    "goal": constitutional_goal,
                    "based_on_mission": self.constitution["Mission"],
                    "original_message_payload": msg.payload # Forward L2's request payload for its own context
                })

class GlobalStrategyLayer(ACELayer):
    def __init__(self, northbound_bus: NorthboundBus, southbound_bus: SouthboundBus, layer_name: str = "GlobalStrategyLayer"):
        super().__init__(northbound_bus, southbound_bus, layer_name)
        self.environmental_context: Dict[str, Any] = {
            'current_conversation_topic': None,
            'user_sentiment': 'neutral',
            'user_model': {}, # Simplified representation of user preferences, history
            'session_history': [] # History of recent interactions
        }

    # Corrected: process_northbound receives from Layer 1 (Aspirational)
    def process_northbound(self, messages: List[Message]):
        print(f"[{self.layer_name}] Received northbound messages (from L1/Aspirational): {messages}")
        for msg in messages:
            goal = msg.payload.get("goal")
            if goal:
                # Acknowledge the goal to Layer 1
                self.send_northbound({ # L2 sends North to L1
                    "status": "acknowledged",
                    "acknowledged_goal": goal,
                    "source_message_payload": msg.payload
                })

                # Update context (simplified)
                # The 'original_message_payload' here is what L1 attached,
                # which should be the payload L2 sent to L1 in its guidance request.
                original_l2_request_payload = msg.payload.get("original_message_payload", {})
                if "user_message" in original_l2_request_payload:
                    user_msg_for_context = original_l2_request_payload["user_message"]
                    self.environmental_context['current_conversation_topic'] = f"topic related to: {user_msg_for_context[:30]}..."

                self.environmental_context['session_history'].append({"type": "goal_received_from_l1", "goal": goal, "context_at_receipt": self.environmental_context.copy()})
                print(f"[{self.layer_name}] Updated context with goal: {goal}, topic: {self.environmental_context['current_conversation_topic']}")

                # Formulate strategic objective based on goal and context
                strategy = f"Strategy: Address L1 goal '{goal}' regarding '{self.environmental_context['current_conversation_topic']}' with current sentiment '{self.environmental_context['user_sentiment']}'."

                if goal == "Increase understanding and clarify user's query effectively and kindly.":
                    strategy = f"Strategy: Proactively clarify query about '{self.environmental_context.get('current_conversation_topic', 'the current topic')}' by providing a simple, kind explanation."
                elif "helpful and positive interaction" in goal:
                    strategy = f"Strategy: Maintain positive interaction and offer assistance regarding '{self.environmental_context.get('current_conversation_topic', 'any topic')}'."

                print(f"[{self.layer_name}] Formulated strategy: {strategy}")
                # Send strategic objective to Layer 3 (Agent Model)
                self.send_southbound({"strategic_objective": strategy, "context": self.environmental_context.copy()}) # L2 sends South to L3
            else:
                print(f"[{self.layer_name}] Received non-goal message from L1: {msg.payload}")

    # Corrected: process_southbound receives from Layer 3 (Agent Model)
    def process_southbound(self, messages: List[Message]):
        print(f"[{self.layer_name}] Received southbound messages (from L3/AgentModel): {messages}")
        for msg in messages:
            # Update environmental_context based on feedback from lower layers (L3)
            if "self_model_update" in msg.payload: # L3 sends self_model_update
                self.environmental_context.update(msg.payload["self_model_update"]) # Example: update L2's context with L3's mood/load
                print(f"[{self.layer_name}] Updated environmental_context with L3 self_model: {msg.payload['self_model_update']}")
            if msg.payload.get("status") == "capability_issue" or msg.payload.get("status") == "limitation_encountered":
                print(f"[{self.layer_name}] Noted capability/limitation issue from L3: {msg.payload}")
                # L2 might need to re-strategize or inform L1. For now, just log.
                # Example: send a status up to L1 if a critical capability for L1's goal is missing
                self.send_northbound({
                    "status": "strategy_feedback_to_l1",
                    "detail": f"L3 reported issue: {msg.payload.get('status')}",
                    "original_L3_payload": msg.payload
                })
            elif msg.payload.get("status") == "action_failure": # L3 might report if an action it commanded (via L4/L5/L6) failed at L3's abstraction
                print(f"[{self.layer_name}] Noted action failure reported by L3: {msg.payload.get('reason')}")
                self.send_northbound({"status": "strategy_adjustment_needed", "reason": f"L3 action failure: {msg.payload.get('reason')}"})
            elif msg.payload.get("status_update_from_l4"): # If L3 is just forwarding L4 status
                 print(f"[{self.layer_name}] Received L4 status via L3: {msg.payload.get('status_update_from_l4')}")
                 # L2 could inspect this if needed.


class AgentModelLayer(ACELayer):
    def __init__(self, northbound_bus: NorthboundBus, southbound_bus: SouthboundBus, layer_name: str = "AgentModelLayer"):
        super().__init__(northbound_bus, southbound_bus, layer_name)
        self.self_model: Dict[str, Any] = {
            'capabilities': ['chat', 'provide_basic_info', 'remember_conversation_context'],
            'current_mood': 'neutral', # Can be 'neutral', 'positive', 'negative', 'confused'
            'load': 0.0, # 0.0 (idle) to 1.0 (max load)
            'available_tools': ['search_web', 'access_database'] # Example tools
        }
        self.episodic_memory: List[Dict[str, Any]] = []

    def process_northbound(self, messages: List[Message]): # From Layer 2 (Global Strategy)
        print(f"[{self.layer_name}] Received northbound messages (from L2/Strategy): {messages}")
        refined_tasks = []
        for msg in messages:
            strategic_objective = msg.payload.get("strategic_objective")
            context = msg.payload.get("context", {})

            if not strategic_objective:
                print(f"[{self.layer_name}] No strategic_objective in message: {msg.payload}")
                continue

            # Store received objective
            self.episodic_memory.append({
                "type": "strategic_objective_received",
                "objective": strategic_objective,
                "context": context,
                "timestamp": "now" # In a real system, use actual timestamps
            })

            # Refine objective based on self_model
            task_details = {"original_objective": strategic_objective}
            can_fully_handle = True

            # Example refinement: Check capabilities
            if "explain" in strategic_objective.lower() and "provide_basic_info" not in self.self_model['capabilities']:
                task_details["refined_objective"] = "Cannot explain: missing capability."
                task_details["status"] = "cannot_perform_capability_missing"
                can_fully_handle = False
                self.send_northbound({
                    "status": "capability_issue",
                    "missing_capability": "provide_basic_info",
                    "requested_objective": strategic_objective
                })
            elif "complex_topic" in strategic_objective.lower() and "explain_complex_topics" not in self.self_model['capabilities']:
                 task_details["refined_objective"] = f"Partially handle: Explain '{context.get('current_conversation_topic', 'topic')}' simply. Cannot do complex explanation."
                 task_details["status"] = "partially_perform_simplification_needed"
                 # Notify L2 about this limitation
                 self.send_northbound({
                    "status": "limitation_encountered",
                    "limitation": "Cannot explain complex topics in depth. Will simplify.",
                    "requested_objective": strategic_objective
                })

            if can_fully_handle:
                task_details["refined_objective"] = f"Execute: {strategic_objective}"
                task_details["status"] = "pending_execution"

            refined_tasks.append(task_details)
            self.send_southbound(task_details) # Send task to Layer 4 (Executive)

            # Store decision
            self.episodic_memory.append({
                "type": "task_formulated",
                "task": task_details,
                "timestamp": "now"
            })

        # Example: Update self_model based on processing load (simplified)
        self.self_model['load'] = min(1.0, self.self_model['load'] + 0.1 * len(messages))
        self.send_northbound({"self_model_update": {"load": self.self_model['load']}})


    def process_southbound(self, messages: List[Message]): # From Layer 4 (Executive Function)
        print(f"[{self.layer_name}] Received southbound messages (from L4/Executive): {messages}")
        for msg in messages:
            self.episodic_memory.append({
                "type": "execution_result_received",
                "result": msg.payload,
                "timestamp": "now"
            })

            task_status = msg.payload.get("status")
            if task_status == "success":
                self.self_model['current_mood'] = 'positive'
                self.self_model['load'] = max(0.0, self.self_model['load'] - 0.05)
            elif task_status == "failure":
                self.self_model['current_mood'] = 'negative'
                self.self_model['load'] = max(0.0, self.self_model['load'] - 0.02) # Less load reduction on failure
                # Send critical failure info to L2
                self.send_northbound({
                    "status": "action_failure", # This matches what GlobalStrategyLayer expects
                    "reason": msg.payload.get("details", "Unknown execution failure"),
                    "original_task": msg.payload.get("original_task")
                })
            elif task_status == "in_progress_update":
                 # Update load or other metrics based on progress
                self.self_model['load'] = msg.payload.get("current_load", self.self_model['load'])


            # Send consolidated status or self_model update to L2
            self.send_northbound({
                "self_model_update": {
                    "current_mood": self.self_model['current_mood'],
                    "load": self.self_model['load']
                },
                "last_task_status": task_status
            })

class ExecutiveFunctionLayer(ACELayer):
    def __init__(self, northbound_bus: NorthboundBus, southbound_bus: SouthboundBus, layer_name: str = "ExecutiveFunctionLayer"):
        super().__init__(northbound_bus, southbound_bus, layer_name)
        self.resource_inventory: Dict[str, Any] = {
            'time_units_available': 100,
            'api_calls_remaining': 1000,
            'cpu_load_avg_short_term': 0.1, # 0.0 to 1.0
            'memory_usage_gb': 0.5
        }
        self.risk_assessment: Dict[str, Any] = {
            'current_risks': [], # e.g., [{"id": "R1", "description": "API rate limit nearing", "severity": "medium"}]
            'mitigation_strategies': {
                "API_RATE_LIMIT": "Reduce frequency of API calls, batch requests."
            }
        }
        self.operational_log: List[str] = [] # For simplicity, just a list of strings

    def _assess_resources(self, task_requirements: Dict[str, Any]) -> bool:
        """Checks if resources are sufficient for the task."""
        required_api_calls = task_requirements.get("api_calls", 0)
        if required_api_calls > self.resource_inventory['api_calls_remaining']:
            self.operational_log.append(f"Resource insufficient: API calls. Required {required_api_calls}, have {self.resource_inventory['api_calls_remaining']}")
            self.send_northbound({
                "status": "resource_issue",
                "detail": f"Not enough API calls. Required: {required_api_calls}, Available: {self.resource_inventory['api_calls_remaining']}",
                "task_requirements": task_requirements
            })
            return False
        # Add more checks for time, cpu, memory etc.
        return True

    def _assess_risks(self, task_details: Dict[str, Any]) -> bool:
        """Identifies and attempts to mitigate risks for the task."""
        if "search_web" in task_details.get("tools_required", []) and self.resource_inventory['api_calls_remaining'] < 10:
            risk_id = f"RISK_API_LOW_{len(self.risk_assessment['current_risks']) + 1}"
            new_risk = {"id": risk_id, "description": "Low API calls remaining, web search might fail.", "severity": "high", "task": task_details.get("original_objective")}
            self.risk_assessment['current_risks'].append(new_risk)
            self.operational_log.append(f"Risk identified: {new_risk['description']}")
            self.send_northbound({
                "status": "risk_identified",
                "risk_details": new_risk
            })
            # Potentially try to apply mitigation or halt task if risk is too high
            if new_risk['severity'] == "high": return False
        return True


    def process_northbound(self, messages: List[Message]): # From Layer 3 (Agent Model)
        print(f"[{self.layer_name}] Received northbound messages (from L3/AgentModel): {messages}")
        for msg in messages:
            task_from_l3 = msg.payload # This is the refined_objective/task from L3

            if not task_from_l3 or not isinstance(task_from_l3, dict):
                print(f"[{self.layer_name}] Invalid task format from L3: {task_from_l3}")
                continue

            original_objective = task_from_l3.get("original_objective", "Unknown objective")
            refined_objective_from_l3 = task_from_l3.get("refined_objective", original_objective)

            self.operational_log.append(f"Received task: {refined_objective_from_l3}")

            # Mock resource/risk assessment (L3 might provide requirements in the payload)
            mock_requirements = {"api_calls": 1} # Assume each task takes 1 API call
            if not self._assess_resources(mock_requirements):
                # If resources not available, task execution might be halted or modified.
                # For now, we'll just log and it won't proceed to generate steps.
                self.send_southbound({
                    "original_task": refined_objective_from_l3,
                    "status": "halted_resource_unavailable",
                    "reason": "API calls exhausted (example)"
                })
                continue

            if not self._assess_risks(task_from_l3):
                self.send_southbound({
                    "original_task": refined_objective_from_l3,
                    "status": "halted_risk_too_high",
                    "reason": "High risk identified (example)"
                })
                continue

            # Develop detailed execution steps (simplified)
            execution_steps = []
            if "Execute: " in refined_objective_from_l3:
                core_task = refined_objective_from_l3.replace("Execute: ", "")
                execution_steps.append(f"Step 1: Initialize resources for '{core_task}'.")
                if "explain" in core_task.lower() or "clarify" in core_task.lower():
                    execution_steps.append(f"Step 2: Query knowledge base for '{context.get('current_conversation_topic', 'topic') if 'context' in task_from_l3 else 'relevant info'}'.")
                    execution_steps.append(f"Step 3: Formulate explanation content.")
                    execution_steps.append(f"Step 4: Verify clarity and conciseness of explanation.")
                elif "search_web" in core_task.lower(): # Assuming task specifies tool
                    execution_steps.append(f"Step 2: Perform web search for '{core_task}'.")
                    execution_steps.append(f"Step 3: Process search results.")
                else:
                    execution_steps.append(f"Step 2: Perform core action for '{core_task}'.")
                execution_steps.append(f"Step 3: Finalize and report completion of '{core_task}'.") # Adjusted step numbering
            else: # If not an "Execute" type task, or other specific prefix
                execution_steps.append(f"Step 1: Analyze non-standard task '{refined_objective_from_l3}'.")
                execution_steps.append(f"Step 2: Determine feasibility and approach.")


            if not execution_steps:
                self.operational_log.append(f"No execution steps generated for: {refined_objective_from_l3}")
                # Send a status update or placeholder if no steps
                self.send_southbound({
                    "original_task": refined_objective_from_l3,
                    "status": "no_steps_generated",
                    "detailed_steps": []
                })
                continue

            detailed_plan_payload = {
                "original_task_from_l3": refined_objective_from_l3,
                "status": "pending_cognitive_control",
                "detailed_steps": execution_steps,
                "resource_allocation": {"api_calls_allocated": mock_requirements["api_calls"]},
                "risk_assessment_summary": "Low" # Placeholder
            }
            self.send_southbound(detailed_plan_payload) # Send to Layer 5 (Cognitive Control)
            self.operational_log.append(f"Sent detailed plan for '{refined_objective_from_l3}' to L5.")

            # Update resource inventory (example)
            self.resource_inventory['api_calls_remaining'] -= mock_requirements["api_calls"]
            self.send_northbound({
                "resource_update": {
                    "api_calls_remaining": self.resource_inventory['api_calls_remaining']
                }
            })

    # This is the CORRECT process_southbound for ExecutiveFunctionLayer,
    # handling messages from L5 (Cognitive Control)
    def process_southbound(self, messages: List[Message]): # From Layer 5 (Cognitive Control)
        print(f"[{self.layer_name}] Received southbound messages (from L5/CognitiveControl): {messages}")
        for msg in messages:
            self.operational_log.append(f"L5 Report: {msg.payload}")

            status = msg.payload.get("status")
            executed_steps_count = msg.payload.get("executed_steps_count", 0) # Assuming L5 might send this
            parent_l4_task_id = msg.payload.get("parent_l4_task_id")

            # Example: Update resource inventory based on L5 reports
            if status == "step_success" or status == "task_complete":
                # Potentially decrease 'time_units_available' or log API calls if L5 reports them.
                self.resource_inventory['cpu_load_avg_short_term'] = max(0.05, self.resource_inventory['cpu_load_avg_short_term'] - 0.01) # Reduced load
            elif status == "step_failure":
                self.resource_inventory['cpu_load_avg_short_term'] = min(0.8, self.resource_inventory['cpu_load_avg_short_term'] + 0.02) # Increased load
                # Log a new risk if a step fails consistently or for critical steps
                new_risk_desc = f"Step failure reported by L5 for L4 task {parent_l4_task_id}: {msg.payload.get('details', 'unknown reason')}"
                risk_id = f"RISK_L5_STEP_FAIL_{len(self.risk_assessment['current_risks']) + 1}"
                current_risk = {"id": risk_id, "description": new_risk_desc, "severity": "low", "details": msg.payload}
                self.risk_assessment['current_risks'].append(current_risk)
                # Send this new risk northbound to L3
                self.send_northbound({
                    "status": "risk_identified",
                    "risk_details": current_risk,
                    "source_layer_event": "L5_step_failure"
                })

            # Send consolidated status/telemetry to L3 (Agent Model)
            # This informs L3 about how L4's plans (executed by L5) are progressing.
            self.send_northbound({
                "status_update_from_l4_via_l5": {
                    "parent_l4_task_id": parent_l4_task_id,
                    "l5_status": status,
                    "details": msg.payload.get("details"),
                    "overall_l4_task_progress_estimate": msg.payload.get("progress_overall") # If L5 sends it
                }
            })


class CognitiveControlLayer(ACELayer):
    def __init__(self, northbound_bus: NorthboundBus, southbound_bus: SouthboundBus, layer_name: str = "CognitiveControlLayer"):
        super().__init__(northbound_bus, southbound_bus, layer_name)
        self.current_task_status: Dict[str, Any] = {
            'task_id': None, # ID of the current sub-task from L4's plan
            'current_step_index': -1,
            'total_steps': 0,
            'progress': 0, # 0-100%
            'active': False,
            'status_details': "Idle" # e.g. "Executing step 2/5", "Error on step 3"
        }
        self.project_plan_overview: List[str] = [] # List of detailed steps from L4
        self.original_l4_task_id: Any = None # To associate with L4's original task

    def _select_and_send_next_task(self, task_id_from_l4: Any):
        """Selects the next step from the project plan and sends it to L6."""
        if self.current_task_status['current_step_index'] < self.current_task_status['total_steps'] - 1:
            self.current_task_status['current_step_index'] += 1
            next_step_detail = self.project_plan_overview[self.current_task_status['current_step_index']]
            self.current_task_status['task_id'] = f"{task_id_from_l4}_step{self.current_task_status['current_step_index']+1}"
            self.current_task_status['active'] = True
            self.current_task_status['progress'] = (self.current_task_status['current_step_index'] / self.current_task_status['total_steps']) * 100
            self.current_task_status['status_details'] = f"Executing step {self.current_task_status['current_step_index']+1}/{self.current_task_status['total_steps']}: {next_step_detail}"

            print(f"[{self.layer_name}] Sending to L6: {next_step_detail}")
            self.send_southbound({
                "task_id": self.current_task_status['task_id'],
                "instruction": next_step_detail,
                "parent_l4_task_id": self.original_l4_task_id
            })
            # Notify L4 about this new step being initiated
            self.send_northbound({
                "status": "step_initiated",
                "task_id": self.current_task_status['task_id'],
                "step_detail": next_step_detail,
                "progress": self.current_task_status['progress'],
                "parent_l4_task_id": self.original_l4_task_id
            })
        else:
            # All steps completed for this L4 task
            self.current_task_status['active'] = False
            self.current_task_status['progress'] = 100
            self.current_task_status['status_details'] = "All steps completed."
            print(f"[{self.layer_name}] All steps completed for L4 task {self.original_l4_task_id}.")
            self.send_northbound({
                "status": "task_complete", # Signifies completion of the L4 task
                "parent_l4_task_id": self.original_l4_task_id,
                "details": "All detailed steps executed."
            })


    def process_northbound(self, messages: List[Message]): # From Layer 4 (Executive Function)
        print(f"[{self.layer_name}] Received northbound messages (from L4/Executive): {messages}")
        for msg in messages:
            l4_payload = msg.payload
            self.original_l4_task_id = l4_payload.get("original_task_from_l3", "L4_Task_Unknown") # Or generate a unique ID

            if l4_payload.get("status") == "pending_cognitive_control":
                self.project_plan_overview = l4_payload.get("detailed_steps", [])
                if not self.project_plan_overview:
                    print(f"[{self.layer_name}] Received plan from L4 but no detailed steps found.")
                    self.send_northbound({
                        "status": "clarification_needed",
                        "detail": "Received plan with no steps.",
                        "parent_l4_task_id": self.original_l4_task_id
                    })
                    continue

                self.current_task_status = {
                    'task_id': None,
                    'current_step_index': -1,
                    'total_steps': len(self.project_plan_overview),
                    'progress': 0,
                    'active': False, # Will become true when first step is sent
                    'status_details': "Plan received, pending first step."
                }
                print(f"[{self.layer_name}] New plan received from L4: {self.project_plan_overview}. Total steps: {self.current_task_status['total_steps']}")

                # Acknowledge receipt and readiness to L4
                self.send_northbound({
                    "status": "plan_acknowledged",
                    "parent_l4_task_id": self.original_l4_task_id,
                    "total_steps_in_plan": self.current_task_status['total_steps']
                })
                # Automatically start the first task
                self._select_and_send_next_task(self.original_l4_task_id)

            elif l4_payload.get("status") in ["halted_resource_unavailable", "halted_risk_too_high", "no_steps_generated"]:
                # L4 indicates it cannot proceed with a task. L5 logs this and informs L4 it's noted.
                self.current_task_status['status_details'] = f"L4 halted plan: {l4_payload.get('status')}"
                self.current_task_status['active'] = False
                self.project_plan_overview = [] # Clear plan
                print(f"[{self.layer_name}] L4 halted plan for {self.original_l4_task_id}: {l4_payload.get('reason', l4_payload.get('status'))}")
                self.send_northbound({
                    "status": "halt_acknowledged_by_l5",
                    "parent_l4_task_id": self.original_l4_task_id,
                    "reason": l4_payload.get('reason', l4_payload.get('status'))
                })


    def process_southbound(self, messages: List[Message]): # From Layer 6 (Task Prosecution)
        print(f"[{self.layer_name}] Received southbound messages (from L6/TaskProsecution): {messages}")
        for msg in messages:
            l6_payload = msg.payload
            reported_task_id = l6_payload.get("task_id")
            status = l6_payload.get("status") # e.g., "success", "failure", "progress_update"
            details = l6_payload.get("details", "")

            if reported_task_id != self.current_task_status['task_id'] or not self.current_task_status['active']:
                print(f"[{self.layer_name}] Received status for unexpected/inactive task {reported_task_id}. Current: {self.current_task_status['task_id']}")
                # Potentially send an error or log this discrepancy
                continue

            self.current_task_status['status_details'] = f"L6 reported: {status} - {details}"

            if status == "success":
                self.current_task_status['progress'] = ((self.current_task_status['current_step_index'] + 1) / self.current_task_status['total_steps']) * 100
                print(f"[{self.layer_name}] Step {self.current_task_status['current_step_index']+1} successful for {self.original_l4_task_id}.")
                self.send_northbound({
                    "status": "step_success",
                    "task_id": reported_task_id,
                    "parent_l4_task_id": self.original_l4_task_id,
                    "details": details,
                    "progress_overall": self.current_task_status['progress']
                })
                # Select and send next task
                self._select_and_send_next_task(self.original_l4_task_id)

            elif status == "failure":
                self.current_task_status['active'] = False # Stop current plan execution on failure
                self.current_task_status['status_details'] = f"Error on task {reported_task_id}: {details}"
                print(f"[{self.layer_name}] Step {self.current_task_status['current_step_index']+1} failed for {self.original_l4_task_id}: {details}")
                self.send_northbound({
                    "status": "step_failure",
                    "task_id": reported_task_id,
                    "parent_l4_task_id": self.original_l4_task_id,
                    "reason": details,
                    "progress_overall": self.current_task_status['progress']
                })
                # Future: Implement more sophisticated error handling, e.g., retry, alternative plan.
                # For now, it just stops processing this L4 plan.

            elif status == "progress_update":
                # Update progress if L6 provides finer-grained updates within a step
                step_progress = l6_payload.get("step_progress", 0) # 0-100 for the current step
                base_progress = (self.current_task_status['current_step_index'] / self.current_task_status['total_steps']) * 100
                self.current_task_status['progress'] = base_progress + (step_progress / self.current_task_status['total_steps'])
                self.send_northbound({
                    "status": "step_progress_update",
                    "task_id": reported_task_id,
                    "parent_l4_task_id": self.original_l4_task_id,
                    "details": details,
                    "current_step_progress": step_progress,
                    "progress_overall": self.current_task_status['progress']
                })
            else:
                print(f"[{self.layer_name}] Received unknown status '{status}' from L6 for task {reported_task_id}")


class TaskProsecutionLayer(ACELayer):
    def __init__(self, northbound_bus: NorthboundBus, southbound_bus: SouthboundBus, layer_name: str = "TaskProsecutionLayer"):
        super().__init__(northbound_bus, southbound_bus, layer_name)
        self.current_task_execution_status: Dict[str, Any] = {
            'task_id': None,
            'status': 'idle', # idle, in_progress, success, failure
            'result': None,
            'error_details': None
        }

    def process_northbound(self, messages: List[Message]): # From Layer 5 (Cognitive Control)
        print(f"[{self.layer_name}] Received northbound messages (from L5/CognitiveControl): {messages}")
        for msg in messages:
            task_id = msg.payload.get("task_id")
            instruction = msg.payload.get("instruction") # This is the string from L5 (e.g., "Step 1: Initialize resources...")
            parent_l4_task_id = msg.payload.get("parent_l4_task_id")

            self.current_task_execution_status = {
                'task_id': task_id,
                'status': 'in_progress',
                'result': None,
                'error_details': None
            }
            print(f"[{self.layer_name}] Executing task: {task_id} - '{instruction}'")

            # "Execution" of the task - for a chatbot, this means generating the text based on the instruction.
            # This is a simplified simulation. A real L6 would do more complex NLP/NLG.
            # We assume the 'instruction' string itself is what the bot should say, or close to it.
            # For more structured tasks, L5 would send a dict like {'action': 'greet', 'name': 'User'}
            # and L6 would have handlers for these actions.

            response_text = ""
            task_successful = True

            # Let's try to parse the instruction if it's a structured command, otherwise use it as is.
            # This is a very basic example of L6 interpreting L5's instruction.
            if isinstance(instruction, str):
                if instruction.startswith("Step 1: Initialize resources for 'Execute: greet user"): # Highly specific parsing
                    response_text = "Hello! How can I help you today?"
                elif instruction.startswith("Step 1: Initialize resources for 'Execute: explain topic X"):
                    response_text = "I will explain topic X. Topic X is a complex subject involving..." # Placeholder
                elif instruction.startswith("Step 1: Analyze non-standard task 'Execute: get_weather"): # Example for a tool
                     response_text = "Okay, I will try to get the weather. Which city?" # Placeholder, no actual tool call
                elif "formulate explanation content" in instruction.lower():
                     response_text = f"Here's an explanation regarding {parent_l4_task_id}." # Generic based on L4 task
                elif "perform core action for" in instruction.lower():
                    core_action = instruction.split("'")[1] if "'" in instruction else "the request"
                    response_text = f"I am now performing the core action for: {core_action}."
                elif "finalize and report completion" in instruction.lower():
                    response_text = f"Finalizing task {task_id}." # Or could be a silent operation
                else:
                    # Default: use the instruction string as the response if it's not a setup/internal step
                    if not (instruction.startswith("Step") and ("Initialize resources" in instruction or "Verify clarity" in instruction)):
                        response_text = instruction
                    else:
                        response_text = f"Completed: {instruction}" # For internal steps, just acknowledge completion

                if not response_text: # If it was an internal step that shouldn't produce direct output
                    response_text = f"Internal step '{instruction}' completed."
                    # This ensures some output is always generated for the simulation if a step is processed.
                    # In a real bot, many L6 actions might be silent.

            elif isinstance(instruction, dict): # More structured command from L5
                action = instruction.get("action")
                details = instruction.get("details", {})
                if action == "greet_user":
                    response_text = f"Hello {details.get('user_name', 'there')}!"
                elif action == "explain_concept":
                    response_text = f"Let me explain {details.get('concept', 'that')}: {details.get('explanation_text', 'It is interesting.')}"
                else:
                    response_text = f"I have received an action '{action}' but don't know how to execute it yet."
                    task_successful = False
                    self.current_task_execution_status['error_details'] = "Unknown action type"
            else:
                response_text = "Error: Received an unparsable instruction."
                task_successful = False
                self.current_task_execution_status['error_details'] = "Unparsable instruction format"

            if task_successful:
                self.current_task_execution_status['status'] = 'success'
                self.current_task_execution_status['result'] = response_text
                print(f"[{self.layer_name}] Task {task_id} successful. Result: {response_text}")
            else:
                self.current_task_execution_status['status'] = 'failure'
                # result might still hold some error message to display
                self.current_task_execution_status['result'] = response_text
                print(f"[{self.layer_name}] Task {task_id} failed. Error: {self.current_task_execution_status['error_details']}")

            # Send completion status and result to L5
            self.send_northbound({
                "task_id": task_id,
                "status": self.current_task_execution_status['status'],
                "result": self.current_task_execution_status['result'], # This is the actual text for the user
                "details": self.current_task_execution_status['error_details'] if not task_successful else "Executed successfully."
            })

            # Conceptually, L6 could send to an environment/actuator here via its southbound_bus
            # For a chatbot, the "result" sent northbound IS the action on the environment (chat UI).
            if self.southbound_bus: # If an environment bus exists
                 self.send_southbound({
                     "action_type": "chat_response_generated",
                     "text_output": self.current_task_execution_status['result'],
                     "source_task_id": task_id
                 })


    def process_southbound(self, messages: List[Message]): # From Environment/Actuators
        # For a simple chatbot, this layer doesn't typically expect southbound messages from an environment.
        # This might be used if the bot could, e.g., receive direct API callbacks or sensor data.
        print(f"[{self.layer_name}] Received southbound messages (from Environment/Actuators): {messages}")
        self.operational_log.append(f"Anomalous L6 Southbound: {messages}")
        # Potentially, this could trigger a northbound message if unexpected interaction occurs.



# This entire duplicate method definition for ExecutiveFunctionLayer.process_southbound
# should be removed as it's the one causing the confusion or being ignored.
# The correct one is now placed before CognitiveControlLayer definition.
