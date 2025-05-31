from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional
import json

from llm_interface import LLMInterface

@dataclass
class Message:
    source_id: str
    target_layer_id: Optional[int] = None
    target_bus_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

class Bus:
    def __init__(self, bus_id: str):
        self.bus_id = bus_id
        self._messages: Deque[Message] = deque()
    def publish(self, message: Message): self._messages.append(message)
    def get_messages(self) -> List[Message]:
        messages = list(self._messages); self._messages.clear(); return messages
    def peek_messages(self) -> List[Message]: return list(self._messages)
    def __repr__(self): return f"<Bus id='{self.bus_id}' messages_count={len(self._messages)}>"

class BusSystem:
    def __init__(self): self._buses: Dict[str, Bus] = {}
    def create_bus(self, bus_id: str) -> Bus:
        if bus_id in self._buses:
            print(f"Warning: Bus ID '{bus_id}' already exists. Returning existing bus.")
            return self._buses[bus_id]
        bus = Bus(bus_id); self._buses[bus_id] = bus; return bus
    def get_bus(self, bus_id: str) -> Optional[Bus]: return self._buses.get(bus_id)
    def publish_to_bus(self, bus_id: str, message: Message):
        bus = self.get_bus(bus_id)
        if bus: bus.publish(message)
        else: print(f"Error: Bus ID '{bus_id}' not found for message from {message.source_id}.")
    def __repr__(self): return f"<BusSystem buses={list(self._buses.keys())}>"

class AgentBot(ABC):
    def __init__(self, agent_id: str, role: str, layer_id: int, bus_system: BusSystem, input_bus_ids: List[str], output_bus_ids: List[str]):
        self.agent_id = agent_id; self.role = role; self.layer_id = layer_id
        self.bus_system = bus_system; self.input_bus_ids = input_bus_ids; self.output_bus_ids = output_bus_ids
        self.memory: Deque[Any] = deque(maxlen=50)
    def read_messages(self) -> List[Message]:
        all_messages: List[Message] = []
        for bus_id in self.input_bus_ids:
            bus = self.bus_system.get_bus(bus_id)
            if bus:
                messages = bus.get_messages()
                if messages: self.log_to_memory(f"Read {len(messages)} from bus '{bus_id}'."); all_messages.extend(messages)
            else: self.log_to_memory(f"Warning: Input bus '{bus_id}' not found.")
        return all_messages
    def send_message(self, bus_id: str, payload: Dict[str, Any], target_layer_id: Optional[int] = None):
        message = Message(source_id=self.agent_id, target_bus_id=bus_id, target_layer_id=target_layer_id, payload=payload)
        self.bus_system.publish_to_bus(bus_id, message)
        log_summary = payload.get('type', payload.get('status', str(list(payload.keys())[0] if payload else 'empty')))
        self.log_to_memory(f"Sent to bus '{bus_id}' (type/summary: {log_summary})")
    @abstractmethod
    def act(self, turn_number: int): pass
    def log_to_memory(self, entry: Any): self.memory.append(entry)
    def __repr__(self): return f"<AgentBot id='{self.agent_id}' role='{self.role}' layer={self.layer_id}>"

class LayerManager:
    def __init__(self): self._layers: Dict[int, List[AgentBot]] = {}
    def add_bot(self, bot: AgentBot):
        if bot.layer_id not in self._layers: self._layers[bot.layer_id] = []
        if any(b.agent_id == bot.agent_id for b in self._layers[bot.layer_id]):
            print(f"Warning: Bot {bot.agent_id} already in layer {bot.layer_id}."); return
        self._layers[bot.layer_id].append(bot)
        self._layers[bot.layer_id].sort(key=lambda x: x.agent_id)
    def get_bots_in_layer(self, layer_id: int) -> List[AgentBot]: return self._layers.get(layer_id, [])
    def get_all_bots(self) -> List[AgentBot]:
        all_bots: List[AgentBot] = []; [all_bots.extend(self._layers[layer_id]) for layer_id in sorted(self._layers.keys())]; return all_bots

class TurnScheduler:
    def __init__(self, layer_manager: LayerManager, bus_system: BusSystem):
        self.layer_manager = layer_manager; self.bus_system = bus_system
        self.layer_processing_order: List[int] = [1, 2, 3, 4, 5, 6]
    def tick(self, turn_number: int):
        print(f"\n--- Turn {turn_number} Start ---")
        for layer_id in self.layer_processing_order:
            bots_in_layer = self.layer_manager.get_bots_in_layer(layer_id)
            if bots_in_layer:
                print(f"  Executing Layer {layer_id} ({len(bots_in_layer)} bots)")
                for bot in bots_in_layer: bot.act(turn_number)
        print(f"--- Turn {turn_number} End ---")

class LLMAgentBot(AgentBot):
    def __init__(self, agent_id: str, role: str, layer_id: int, bus_system: BusSystem, input_bus_ids: List[str], output_bus_ids: List[str], llm_interface: LLMInterface, system_prompt: str):
        super().__init__(agent_id, role, layer_id, bus_system, input_bus_ids, output_bus_ids)
        self.llm_interface = llm_interface; self.system_prompt = system_prompt
        self.current_llm_response: Optional[str] = None
    def get_formatted_memory_context(self, num_entries=3) -> str:
        if not self.memory: return "No recent memory entries."
        relevant_memory = list(self.memory)[-num_entries:]
        return f"Relevant Recent Memory:\n" + "\n".join(map(str, relevant_memory))
    @abstractmethod
    def generate_llm_user_prompt(self, turn_number: int, received_messages: List[Message]) -> Optional[str]: pass
    @abstractmethod
    def parse_llm_response(self, llm_response_text: str) -> Dict[str, Any]: pass
    @abstractmethod
    def take_action_from_parsed_response(self, turn_number: int, parsed_response: Dict[str, Any], original_messages: List[Message]): pass
    def act(self, turn_number: int):
        self.log_to_memory(f"T{turn_number}: {self.agent_id} ({self.role}) starting.")
        received_messages = self.read_messages()
        if not received_messages and not self.should_act_without_messages():
            self.log_to_memory(f"T{turn_number}: No messages and not configured to act autonomously. Turn ended."); return
        user_prompt = self.generate_llm_user_prompt(turn_number, received_messages)
        if user_prompt:
            self.log_to_memory(f"T{turn_number}: LLM_PROMPT_USER: {user_prompt[:150]}...")
            llm_response_text = self.llm_interface.respond(system_prompt=self.system_prompt, user_prompt=user_prompt)
            self.current_llm_response = llm_response_text
            self.log_to_memory(f"T{turn_number}: LLM_RESPONSE_RAW: {str(llm_response_text)[:150]}...")
            if llm_response_text and not llm_response_text.startswith("Error:") and not llm_response_text.startswith("LLM not configured."):
                try:
                    parsed_response = self.parse_llm_response(llm_response_text)
                    self.log_to_memory(f"T{turn_number}: LLM_RESPONSE_PARSED: {str(parsed_response)[:150]}...")
                    self.take_action_from_parsed_response(turn_number, parsed_response, received_messages)
                except Exception as e: self.log_to_memory(f"T{turn_number}: ERROR: Parsing/Action failed: {e}"); self.handle_llm_failure(turn_number, received_messages, llm_response_text, e)
            else: self.log_to_memory(f"T{turn_number}: ERROR: LLM response error/empty: '{llm_response_text}'."); self.handle_llm_failure(turn_number, received_messages, llm_response_text)
        else: self.log_to_memory(f"T{turn_number}: No user prompt. Performing non-LLM actions."); self.perform_non_llm_actions(turn_number, received_messages)
        self.log_to_memory(f"T{turn_number}: {self.agent_id} ({self.role}) ended turn.")
    def should_act_without_messages(self) -> bool: return False
    def handle_llm_failure(self, turn_number: int, tội_messages: List[Message], llm_response_text: Optional[str]=None, exception: Optional[Exception]=None): self.log_to_memory(f"T{turn_number}: Default LLM failure. LLM response: '{llm_response_text}'. Exc: {exception}")
    def perform_non_llm_actions(self, turn_number: int, tội_messages: List[Message]): self.log_to_memory(f"T{turn_number}: Default non-LLM action.")

class L1_LLMSupervisorBot(LLMAgentBot):
    L1_SYSTEM_PROMPT = """
You are the L1 Supervisor Bot... [Content as provided in subtask description] ...
"""
    def __init__(self, agent_id: str, bus_system: BusSystem, layer_manager: LayerManager, llm_interface: LLMInterface, user_input_bus_id: str, l1_l2_bus_id: str):
        super().__init__(agent_id=agent_id, role="L1_LLMSupervisor", layer_id=1, bus_system=bus_system, input_bus_ids=[user_input_bus_id], output_bus_ids=[l1_l2_bus_id], llm_interface=llm_interface, system_prompt=self.L1_SYSTEM_PROMPT)
        self.layer_manager = layer_manager; self.l1_l2_bus_id = l1_l2_bus_id; self.created_bots_count = 0
    def generate_llm_user_prompt(self, turn_number: int, received_messages: List[Message]) -> Optional[str]:
        if not received_messages: return None
        user_text = next((msg.payload.get('text','') for msg in received_messages if msg.payload.get("type") == "user_utterance"), "")
        if not user_text: return None
        memory_context = self.get_formatted_memory_context(num_entries=2)
        prompt = f"{memory_context}\n\nUser Input (Turn {turn_number}): \"{user_text}\"\n\nBased on the user input and your memory, provide your analysis in the specified JSON format."
        self.log_to_memory(f"T{turn_number}: L1 Prompting with user text: '{user_text[:50]}...' and memory.")
        return prompt
    def parse_llm_response(self, llm_response_text: str) -> Dict[str, Any]:
        self.log_to_memory(f"L1 Parsing LLM response: {llm_response_text[:100]}...")
        try:
            text = llm_response_text.strip(); text = text[7:-3] if text.startswith("```json") and text.endswith("```") else text
            parsed = json.loads(text)
            if "l2_directive" not in parsed or "goal" not in parsed["l2_directive"]:
                 parsed["l2_directive"] = parsed.get("l2_directive", {})
                 parsed["l2_directive"]["goal"] = parsed["l2_directive"].get("goal", "L1 Error: LLM goal missing.")
                 parsed["l2_directive"]["details"] = parsed["l2_directive"].get("details", llm_response_text)
            return parsed
        except Exception as e: self.log_to_memory(f"L1 JSON/Parsing Error: {e}. Raw: {llm_response_text}"); return {"error": str(e), "raw_response": llm_response_text, "l2_directive": {"goal": "L1 Error: Parsing Exception. Relay raw.", "details": llm_response_text}}
    def take_action_from_parsed_response(self, turn_number: int, parsed_response: Dict[str, Any], original_messages: List[Message]):
        l2_directive = parsed_response.get("l2_directive", {}); original_user_input_payload = next((msg.payload for msg in original_messages if msg.payload.get("type") == "user_utterance"), original_messages[0].payload if original_messages else {})
        l2_payload = {'type': 'l1_directive', 'goal': l2_directive.get('goal'), 'details': l2_directive.get('details'), 'user_intent': parsed_response.get('user_intent'), 'turn': turn_number, 'original_user_input': original_user_input_payload}
        self.send_message(self.l1_l2_bus_id, l2_payload)
        self.log_to_memory(f"T{turn_number}: ACTION: Sent directive to L2 ({self.l1_l2_bus_id}) goal: {l2_payload['goal'][:50]}...")
        creation_requests = parsed_response.get("dynamic_creation_request", [])
        if isinstance(creation_requests, list):
            for req in creation_requests:
                if isinstance(req, dict) and req.get("layer_to_create_in") == 2 and req.get("requested_role"):
                    self.created_bots_count += 1; new_bot_id = f"{req['requested_role']}_Dyn_{self.created_bots_count}"
                    l2_out_bus = "L2_S_L3_N"; self.bus_system.create_bus(l2_out_bus) # Ensure bus exists
                    # For MVP, dynamic creation uses L1_InputParserBot as a stand-in for specific roles.
                    # This needs a proper factory or class mapping in a real system.
                    new_bot = L1_InputParserBot(agent_id=new_bot_id, bus_system=self.bus_system, user_input_bus_id=self.l1_l2_bus_id, l1_l2_bus_id=l2_out_bus)
                    new_bot.role = req['requested_role'] # Set role
                    self.layer_manager.add_bot(new_bot)
                    self.log_to_memory(f"T{turn_number}: ACTION: Created {new_bot_id} in L2 for goal: {req.get('initial_goal_for_new_bot')}")

class L2_LLMStrategyBot(LLMAgentBot):
    L2_SYSTEM_PROMPT = """
You are the L2 Strategy Bot... [Content as provided] ...
"""
    def __init__(self, agent_id: str, bus_system: BusSystem, llm_interface: LLMInterface, input_bus_id: str, output_to_l3_bus_id: str, output_to_l1_bus_id: str):
        super().__init__(agent_id=agent_id, role="L2_LLMStrategy", layer_id=2, bus_system=bus_system, input_bus_ids=[input_bus_id], output_bus_ids=[output_to_l3_bus_id, output_to_l1_bus_id], llm_interface=llm_interface, system_prompt=self.L2_SYSTEM_PROMPT)
        self.output_to_l3_bus_id = output_to_l3_bus_id; self.output_to_l1_bus_id = output_to_l1_bus_id
    def generate_llm_user_prompt(self, turn_number: int, received_messages: List[Message]) -> Optional[str]:
        if not received_messages: return None
        l1_directive = received_messages[0].payload; memory_context = self.get_formatted_memory_context(num_entries=3)
        prompt = f"{memory_context}\n\nL1 Directive (Turn {turn_number}): {json.dumps(l1_directive)}\n\nFormulate a strategy. Output JSON."
        self.log_to_memory(f"T{turn_number}: L2 Formatting prompt with L1 directive and memory.")
        return prompt
    def parse_llm_response(self, llm_response_text: str) -> Dict[str, Any]:
        self.log_to_memory(f"L2 Parsing: {llm_response_text[:100]}...");
        try: return json.loads(llm_response_text.strip().lstrip("```json").rstrip("```"))
        except Exception as e: self.log_to_memory(f"L2 JSON/Parsing Error: {e}"); return {"error": str(e), "raw_response": llm_response_text}
    def take_action_from_parsed_response(self, turn_number: int, parsed_response: Dict[str, Any], original_messages: List[Message]):
        if parsed_response.get("error"): self.send_message(self.output_to_l3_bus_id, {'type': 'l2_error', 'details': parsed_response}); self.log_to_memory(f"T{turn_number}: ACTION: L2 Sent error to L3."); return
        if parsed_response.get("steps_for_l3"): self.send_message(self.output_to_l3_bus_id, {'type': 'l2_plan', **parsed_response}); self.log_to_memory(f"T{turn_number}: ACTION: L2 Sent plan to L3.")
        if parsed_response.get("context_summary_for_l1"): self.send_message(self.output_to_l1_bus_id, {'type': 'l2_status', 'summary': parsed_response["context_summary_for_l1"]}); self.log_to_memory(f"T{turn_number}: ACTION: L2 Sent status to L1.")

class L3_LLMAgentModelBot(LLMAgentBot):
    L3_SYSTEM_PROMPT = """
You are the L3 Agent Model Bot... [Content as provided] ...
"""
    def __init__(self, agent_id: str, bus_system: BusSystem, llm_interface: LLMInterface, input_bus_id: str, output_to_l4_bus_id: str, output_to_l2_bus_id: str):
        super().__init__(agent_id=agent_id, role="L3_LLMAgentModel", layer_id=3, bus_system=bus_system, input_bus_ids=[input_bus_id], output_bus_ids=[output_to_l4_bus_id, output_to_l2_bus_id], llm_interface=llm_interface, system_prompt=self.L3_SYSTEM_PROMPT)
        self.capabilities = {"can_query_database": True, "can_generate_text": True, "can_perform_complex_analysis": False}
        self.output_to_l4_bus_id = output_to_l4_bus_id; self.output_to_l2_bus_id = output_to_l2_bus_id
    def generate_llm_user_prompt(self, turn_number: int, received_messages: List[Message]) -> Optional[str]:
        if not received_messages: return None
        l2_payload = received_messages[0].payload; memory_context = self.get_formatted_memory_context(num_entries=3)
        prompt = f"{memory_context}\n\nL2 Strategic Steps (Turn {turn_number}): {json.dumps(l2_payload)}\nMy capabilities: {json.dumps(self.capabilities)}\n\nRefine plan for L4. Output JSON."
        self.log_to_memory(f"T{turn_number}: L3 Formatting prompt with L2 steps, capabilities, and memory.")
        return prompt
    def parse_llm_response(self, llm_response_text: str) -> Dict[str, Any]:
        self.log_to_memory(f"L3 Parsing: {llm_response_text[:100]}...");
        try: return json.loads(llm_response_text.strip().lstrip("```json").rstrip("```"))
        except Exception as e: self.log_to_memory(f"L3 JSON/Parsing Error: {e}"); return {"error": str(e), "raw_response": llm_response_text}
    def take_action_from_parsed_response(self, turn_number: int, parsed_response: Dict[str, Any], original_messages: List[Message]):
        if parsed_response.get("error"): self.send_message(self.output_to_l4_bus_id, {'type': 'l3_error', 'details': parsed_response}); self.log_to_memory(f"T{turn_number}: ACTION: L3 Sent error to L4."); return
        if parsed_response.get("refined_plan_for_l4"): self.send_message(self.output_to_l4_bus_id, {'type': 'l3_plan', **parsed_response}); self.log_to_memory(f"T{turn_number}: ACTION: L3 Sent plan to L4.")
        if parsed_response.get("capability_summary_for_l2"): self.send_message(self.output_to_l2_bus_id, {'type': 'l3_status', 'summary': parsed_response["capability_summary_for_l2"]}); self.log_to_memory(f"T{turn_number}: ACTION: L3 Sent status to L2.")

class L4_LLMExecutiveBot(LLMAgentBot):
    L4_SYSTEM_PROMPT = """
You are the L4 Executive Function Bot... [Content as provided] ...
"""
    def __init__(self, agent_id: str, bus_system: BusSystem, llm_interface: LLMInterface, input_bus_id: str, output_to_l5_bus_id: str, output_to_l3_bus_id: str):
        super().__init__(agent_id=agent_id, role="L4_LLMExecutive", layer_id=4, bus_system=bus_system, input_bus_ids=[input_bus_id], output_bus_ids=[output_to_l5_bus_id, output_to_l3_bus_id], llm_interface=llm_interface, system_prompt=self.L4_SYSTEM_PROMPT)
        self.output_to_l5_bus_id = output_to_l5_bus_id; self.output_to_l3_bus_id = output_to_l3_bus_id
    def generate_llm_user_prompt(self, turn_number: int, received_messages: List[Message]) -> Optional[str]:
        if not received_messages: return None
        l3_payload = received_messages[0].payload; memory_context = self.get_formatted_memory_context(num_entries=3)
        prompt = f"{memory_context}\n\nL3 Refined Plan (Turn {turn_number}): {json.dumps(l3_payload)}\n\nDetail executable tasks for L5. Output JSON."
        self.log_to_memory(f"T{turn_number}: L4 Formatting prompt with L3 plan and memory.")
        return prompt
    def parse_llm_response(self, llm_response_text: str) -> Dict[str, Any]:
        self.log_to_memory(f"L4 Parsing: {llm_response_text[:100]}...");
        try: return json.loads(llm_response_text.strip().lstrip("```json").rstrip("```"))
        except Exception as e: self.log_to_memory(f"L4 JSON/Parsing Error: {e}"); return {"error": str(e), "raw_response": llm_response_text}
    def take_action_from_parsed_response(self, turn_number: int, parsed_response: Dict[str, Any], original_messages: List[Message]):
        if parsed_response.get("error"): self.send_message(self.output_to_l5_bus_id, {'type': 'l4_error', 'details': parsed_response}); self.log_to_memory(f"T{turn_number}: ACTION: L4 Sent error to L5."); return
        if parsed_response.get("detailed_tasks_for_l5"): self.send_message(self.output_to_l5_bus_id, {'type': 'l4_tasks', **parsed_response}); self.log_to_memory(f"T{turn_number}: ACTION: L4 Sent tasks to L5.")
        if parsed_response.get("resource_status_for_l3"): self.send_message(self.output_to_l3_bus_id, {'type': 'l4_status', 'summary': parsed_response["resource_status_for_l3"]}); self.log_to_memory(f"T{turn_number}: ACTION: L4 Sent status to L3.")

class L5_LLMCognitiveControlBot(LLMAgentBot):
    L5_SYSTEM_PROMPT = """
You are the L5 Cognitive Control Bot... [Content as provided] ...
"""
    def __init__(self, agent_id: str, bus_system: BusSystem, llm_interface: LLMInterface, input_bus_id: str, output_to_l6_bus_id: str, output_to_l4_bus_id: str):
        super().__init__(agent_id=agent_id, role="L5_LLMCognitiveControl", layer_id=5, bus_system=bus_system, input_bus_ids=[input_bus_id], output_bus_ids=[output_to_l6_bus_id, output_to_l4_bus_id], llm_interface=llm_interface, system_prompt=self.L5_SYSTEM_PROMPT)
        self.output_to_l6_bus_id = output_to_l6_bus_id; self.output_to_l4_bus_id = output_to_l4_bus_id
    def generate_llm_user_prompt(self, turn_number: int, received_messages: List[Message]) -> Optional[str]:
        if not received_messages: return None
        l4_payload = received_messages[0].payload; memory_context = self.get_formatted_memory_context(num_entries=3)
        prompt = f"{memory_context}\n\nL4 Detailed Tasks (Turn {turn_number}): {json.dumps(l4_payload)}\n\nSelect first task and prepare instruction for L6. Output JSON."
        self.log_to_memory(f"T{turn_number}: L5 Formatting prompt with L4 tasks and memory.")
        return prompt
    def parse_llm_response(self, llm_response_text: str) -> Dict[str, Any]:
        self.log_to_memory(f"L5 Parsing: {llm_response_text[:100]}...");
        try: return json.loads(llm_response_text.strip().lstrip("```json").rstrip("```"))
        except Exception as e: self.log_to_memory(f"L5 JSON/Parsing Error: {e}"); return {"error": str(e), "raw_response": llm_response_text}
    def take_action_from_parsed_response(self, turn_number: int, parsed_response: Dict[str, Any], original_messages: List[Message]):
        if parsed_response.get("error"): self.send_message(self.output_to_l6_bus_id, {'type': 'l5_error', 'details': parsed_response}); self.log_to_memory(f"T{turn_number}: ACTION: L5 Sent error to L6."); return
        if parsed_response.get("instruction_for_l6"): self.send_message(self.output_to_l6_bus_id, parsed_response["instruction_for_l6"]); self.log_to_memory(f"T{turn_number}: ACTION: L5 Sent instruction to L6.")
        if parsed_response.get("task_selection_update_for_l4"): self.send_message(self.output_to_l4_bus_id, {'type': 'l5_status', 'summary': parsed_response["task_selection_update_for_l4"]}); self.log_to_memory(f"T{turn_number}: ACTION: L5 Sent status to L4.")

class L6_LLMOutputBot(LLMAgentBot):
    L6_SYSTEM_PROMPT = """
You are the L6 Output Bot... [Content as provided] ...
"""
    def __init__(self, agent_id: str, bus_system: BusSystem, llm_interface: LLMInterface, l5_l6_bus_id: str, system_output_bus_id: str):
        super().__init__(agent_id=agent_id, role="L6_LLMOutput", layer_id=6, bus_system=bus_system, input_bus_ids=[l5_l6_bus_id], output_bus_ids=[system_output_bus_id], llm_interface=llm_interface, system_prompt=self.L6_SYSTEM_PROMPT)
    def generate_llm_user_prompt(self, turn_number: int, received_messages: List[Message]) -> Optional[str]:
        if not received_messages: return None
        l5_instruction = received_messages[0].payload; memory_context = self.get_formatted_memory_context(num_entries=2)
        prompt = f"{memory_context}\n\nL5 Instruction for L6 (Turn {turn_number}): {json.dumps(l5_instruction)}\n\nGenerate a user-facing natural language response. Output JSON."
        self.log_to_memory(f"T{turn_number}: L6 Formatting prompt with L5 instruction and memory.")
        return prompt
    def parse_llm_response(self, llm_response_text: str) -> Dict[str, Any]:
        self.log_to_memory(f"L6 Parsing: {llm_response_text[:100]}...");
        try:
            data = json.loads(llm_response_text.strip().lstrip("```json").rstrip("```"))
            if "final_user_response" not in data: return {"error": "missing_key", "final_user_response": "L6 Error: LLM missing key."}
            return data
        except Exception as e: self.log_to_memory(f"L6 JSON/Parsing Error: {e}"); return {"error": str(e), "raw_response": llm_response_text, "final_user_response": "L6 Error: Parsing Exception."}
    def take_action_from_parsed_response(self, turn_number: int, parsed_response: Dict[str, Any], original_messages: List[Message]):
        response_text = parsed_response.get("final_user_response", "L6: I'm not sure how to respond.")
        output_payload = {'text': response_text, 'source_L6_agent': self.agent_id, 'generating_turn': turn_number}
        if self.output_bus_ids: self.send_message(self.output_bus_ids[0], output_payload); self.log_to_memory(f"T{turn_number}: ACTION: L6 Sent to UI: '{response_text[:50]}...'")
        else: self.log_to_memory(f"T{turn_number}: ACTION_FAIL: L6 No output bus configured.")
