from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

# Comment out old ACE framework imports
# from ace_framework import (
#     ACELayer, Message as OldMessage, NorthboundBus as OldNorthboundBus, SouthboundBus as OldSouthboundBus,
#     AspirationalLayer, GlobalStrategyLayer, AgentModelLayer, ExecutiveFunctionLayer,
#     CognitiveControlLayer, TaskProsecutionLayer
# )

# Import new agent system classes
from agent_system import (
    Message, Bus, BusSystem, AgentBot, LayerManager, TurnScheduler,
    L1_LLMSupervisorBot,
    L2_LLMStrategyBot, L3_LLMAgentModelBot, L4_LLMExecutiveBot, L5_LLMCognitiveControlBot,
    L6_LLMOutputBot # Ensure this matches the new class name in agent_system.py
)
from llm_interface import LLMInterface
from kivy.clock import Clock
from kivy.utils import escape_markup

# Bot class is removed as ChatApp will manage the ACE system directly.

class ChatApp(App):
    def build(self):
        self.bus_system = BusSystem()
        self.layer_manager = LayerManager()
        self.current_turn_number = 0

        # Define Monitored Buses (using generic names for a single ACE system)
        self.monitored_bus_ids = [
            "USER_INPUT_BUS",
            "L1_S_L2_N", "L2_N_L1_S", # L1-L2
            "L2_S_L3_N", "L3_N_L2_S", # L2-L3
            "L3_S_L4_N", "L4_N_L3_S", # L3-L4
            "L4_S_L5_N", "L5_N_L4_S", # L4-L5
            "L5_S_L6_N", "L6_N_L5_S", # L5-L6
            "SYSTEM_OUTPUT_BUS"
        ]
        # Create all defined buses
        for bus_id in self.monitored_bus_ids:
            self.bus_system.create_bus(bus_id)

        # Instantiate LLMInterface
        self.llm_interface = LLMInterface()
        if self.llm_interface.client is None:
            print("-" * 60)
            print("WARNING: LLMInterface client is not initialized.")
            print("The LLM-powered agents will not function correctly.")
            print("Please ensure OPENAI_API_KEY and OPENAI_BASE_URL environment variables are set.")
            print("If using a non-OpenAI provider with an OpenAI-compatible API,")
            print("ensure OPENAI_BASE_URL points to the correct endpoint.")
            print("Example for Google's Gemini (if you have access and a key):")
            print("  OPENAI_API_KEY='your_google_api_key_for_gemini'")
            print("  OPENAI_BASE_URL='https://generativelanguage.googleapis.com/v1beta'")
            print("  (Note: The model name in llm_interface.py might also need adjustment, e.g., 'gemini-1.0-pro-latest')")
            print("-" * 60)
        else:
            print("-" * 60)
            print("INFO: LLMInterface client initialized successfully.")
            print(f"INFO: Using LLM Base URL: {self.llm_interface.base_url}")
            print("-" * 60)

        # Instantiate and Add AgentBots
        # Layer 1
        l1_bot = L1_LLMSupervisorBot(
            agent_id="L1_Supervisor_1",
            bus_system=self.bus_system,
            layer_manager=self.layer_manager,
            llm_interface=self.llm_interface,
            user_input_bus_id="USER_INPUT_BUS",
            l1_l2_bus_id="L1_S_L2_N" # Southbound to L2
        )
        self.layer_manager.add_bot(l1_bot)

        # Layer 2: LLMStrategyBot
        l2_bot = L2_LLMStrategyBot(
            agent_id="L2_Strategy_1",
            bus_system=self.bus_system,
            llm_interface=self.llm_interface,
            input_bus_id="L1_S_L2_N",          # Northbound from L1
            output_to_l3_bus_id="L2_S_L3_N",   # Southbound to L3
            output_to_l1_bus_id="L2_N_L1_S"    # Northbound to L1 (for acks, status)
        )
        self.layer_manager.add_bot(l2_bot)

        # Layer 3: LLMAgentModelBot
        l3_bot = L3_LLMAgentModelBot(
            agent_id="L3_AgentModel_1",
            bus_system=self.bus_system,
            llm_interface=self.llm_interface,
            input_bus_id="L2_S_L3_N",          # Northbound from L2
            output_to_l4_bus_id="L3_S_L4_N",   # Southbound to L4
            output_to_l2_bus_id="L3_N_L2_S"    # Northbound to L2
        )
        self.layer_manager.add_bot(l3_bot)

        # Layer 4: LLMExecutiveBot
        l4_bot = L4_LLMExecutiveBot(
            agent_id="L4_Executive_1",
            bus_system=self.bus_system,
            llm_interface=self.llm_interface,
            input_bus_id="L3_S_L4_N",          # Northbound from L3
            output_to_l5_bus_id="L4_S_L5_N",   # Southbound to L5
            output_to_l3_bus_id="L4_N_L3_S"    # Northbound to L3
        )
        self.layer_manager.add_bot(l4_bot)

        # Layer 5: LLMCognitiveControlBot
        l5_bot = L5_LLMCognitiveControlBot(
            agent_id="L5_CognitiveControl_1",
            bus_system=self.bus_system,
            llm_interface=self.llm_interface,
            input_bus_id="L4_S_L5_N",          # Northbound from L4
            output_to_l6_bus_id="L5_S_L6_N",   # Southbound to L6
            output_to_l4_bus_id="L5_N_L4_S"    # Northbound to L4
        )
        self.layer_manager.add_bot(l5_bot)

        # Layer 6: L6_LLMOutputBot
        l6_bot = L6_LLMOutputBot( # Ensure this class name matches the one in agent_system.py
            agent_id="L6_Output_1",
            bus_system=self.bus_system,
            llm_interface=self.llm_interface,
            l5_l6_bus_id="L5_S_L6_N",
            system_output_bus_id="SYSTEM_OUTPUT_BUS"
        )
        self.layer_manager.add_bot(l6_bot)

        self.turn_scheduler = TurnScheduler(layer_manager=self.layer_manager, bus_system=self.bus_system)

        self.root_widget = RootWidget()

        Clock.schedule_interval(self.run_ace_turn, 1.0) # Run ACE tick every 1 second
        Clock.schedule_interval(self.update_ui_elements, 0.2) # Update UI every 0.2 seconds

        Clock.schedule_once(self.update_ui_elements, 0) # Initial UI population on next frame
        return self.root_widget

    def run_ace_turn(self, dt=None):
        self.turn_scheduler.tick(self.current_turn_number)
        self.current_turn_number += 1
        # self.update_ui_elements() # UI is updated by its own clock schedule

    def update_ui_elements(self, dt=None):
        if not hasattr(self, 'root_widget') or self.root_widget is None:
            return

        # Update Layer Panels
        for i in range(1, 7):
            layer_bots_label = getattr(self.root_widget.ids, f'layer_{i}_bots_label', None)
            if layer_bots_label:
                bots_in_layer = self.layer_manager.get_bots_in_layer(i)
                if bots_in_layer:
                    bot_details = [f"- {escape_markup(b.agent_id)} ({escape_markup(b.role)})" for b in bots_in_layer]
                    layer_bots_label.text = "\n".join(bot_details)
                else:
                    layer_bots_label.text = f"L{i} Bots: (No agents)"

        # Update Bus Content Display
        bus_texts = []
        # Ensure all monitored buses are created if not already (though they should be in build)
        for bus_id in self.monitored_bus_ids:
            self.bus_system.create_bus(bus_id) # Safe call: returns existing if already there

        for bus_id in self.monitored_bus_ids:
            bus = self.bus_system.get_bus(bus_id)
            if bus:
                messages = bus.peek_messages()
                bus_texts.append(f"[b]{escape_markup(bus_id)}[/b] ({len(messages)} msgs):")
                if messages:
                    for msg in messages[-3:]: # Show last 3 messages
                        payload_preview = str(msg.payload)[:60] + "..." if len(str(msg.payload)) > 60 else str(msg.payload)
                        bus_texts.append(f"  - Src: {escape_markup(msg.source_id)}, Payload: {escape_markup(payload_preview)}")
                else:
                    bus_texts.append("  (empty)")
            else:
                bus_texts.append(f"[b]{escape_markup(bus_id)}[/b]: (Not found!)")

        bus_label = self.root_widget.ids.get('bus_content_label')
        if bus_label:
            bus_label.text = "\n".join(bus_texts)

        # Update Chat History from SYSTEM_OUTPUT_BUS
        system_output_bus = self.bus_system.get_bus("SYSTEM_OUTPUT_BUS")
        if system_output_bus:
            output_messages = system_output_bus.get_messages() # Consume messages
            for msg in output_messages:
                if 'text' in msg.payload:
                    chat_history = self.root_widget.ids.get('chat_history_label')
                    if chat_history:
                        chat_history.text += f"System: {escape_markup(msg.payload['text'])}\n"

        # Display memory for L1_Supervisor_1
        bot_memory_widget = self.root_widget.ids.get('bot_memory_label')
        if bot_memory_widget:
            supervisor_bot_id = "L1_Supervisor_1"
            l1_bots = self.layer_manager.get_bots_in_layer(1)
            supervisor_bot = next((bot for bot in l1_bots if bot.agent_id == supervisor_bot_id), None)

            if supervisor_bot:
                memory_text = f"Memory of {escape_markup(supervisor_bot.agent_id)} (last 10):\n"
                formatted_entries = []
                # Display last 10 memory entries
                for entry_idx, entry_item in enumerate(list(supervisor_bot.memory)[-10:]):
                    entry_str = str(entry_item) # Ensure it's a string
                    prefix = "  "
                    if "LLM_PROMPT_USER:" in entry_str:
                        prefix = "  [PROMPT] "
                        entry_str = entry_str.replace("LLM_PROMPT_USER:", "").strip()
                    elif "LLM_RESPONSE_RAW:" in entry_str:
                        prefix = "  [LLM RAW] "
                        entry_str = entry_str.replace("LLM_RESPONSE_RAW:", "").strip()
                    elif "LLM_RESPONSE_PARSED:" in entry_str:
                        prefix = "  [LLM PARSED] "
                        entry_str = entry_str.replace("LLM_RESPONSE_PARSED:", "").strip()
                    elif "ACTION:" in entry_str: # Generic action keyword
                        prefix = "  [ACTION] "
                        entry_str = entry_str.replace("ACTION:", "").strip()
                    elif "T" == entry_str.strip()[:1] and ":" in entry_str.split(" ")[0]: # Heuristic for Turn logs
                        parts = entry_str.split(":", 1)
                        prefix = f"  [{parts[0].strip()}] "
                        entry_str = parts[1].strip() if len(parts) > 1 else ""

                    # Truncate long entries for display
                    entry_display = (entry_str[:70] + '...') if len(entry_str) > 70 else entry_str
                    formatted_entries.append(f"{prefix}{escape_markup(entry_display)}")

                memory_text += "\n".join(formatted_entries)
                bot_memory_widget.text = memory_text
            else:
                bot_memory_widget.text = f"{supervisor_bot_id} not found in Layer 1."


    def send_message(self, message_text):
        if message_text.strip():
            chat_history = self.root_widget.ids.get('chat_history_label')
            if chat_history:
                chat_history.text += f"You: {escape_markup(message_text)}\n"
            message_input_widget = self.root_widget.ids.get('message_input')
            if message_input_widget:
                message_input_widget.text = ""

            user_msg_payload = {'type': 'user_utterance', 'text': message_text}
            msg_obj = Message(source_id='user_gui', payload=user_msg_payload, target_bus_id="USER_INPUT_BUS")

            self.bus_system.publish_to_bus("USER_INPUT_BUS", msg_obj)

            # Optional: Force an immediate (partial) run & UI update if clock is too slow for perceived responsiveness
            # self.run_ace_turn()
            # self.update_ui_elements()


class RootWidget(BoxLayout):
    pass

if __name__ == '__main__':
    ChatApp().run()
