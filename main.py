from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from ace_framework import (
    ACELayer, Message, NorthboundBus, SouthboundBus,
    AspirationalLayer, GlobalStrategyLayer, AgentModelLayer, ExecutiveFunctionLayer,
    CognitiveControlLayer, TaskProsecutionLayer
)

class Bot:
    def __init__(self, name: str):
        self.name = name

        # Buses between Layer 1 (Aspirational) and Layer 2 (Global Strategy)
        self.northbound_bus_L1_L2 = NorthboundBus()
        self.southbound_bus_L1_L2 = SouthboundBus()

        # Buses between Layer 2 (Global Strategy) and Layer 3 (Agent Model)
        self.northbound_bus_L2_L3 = NorthboundBus()
        self.southbound_bus_L2_L3 = SouthboundBus()

        # Initialize Layer 1: Aspirational Layer
        self.aspirational_layer = AspirationalLayer(
            northbound_bus=self.northbound_bus_L1_L2, # Receives from Layer 2
            southbound_bus=self.southbound_bus_L1_L2  # Sends to Layer 2
        )

        # Initialize Layer 2: Global Strategy Layer
        self.strategy_layer = GlobalStrategyLayer(
            northbound_bus=self.southbound_bus_L1_L2,  # Receives from Layer 1 (L1 Southbound is L2 Northbound)
            southbound_bus=self.northbound_bus_L1_L2   # Sends to Layer 1 (L1 Northbound is L2 Southbound for acks)
                                                       # This seems wrong, L2 southbound should be to L3.
                                                       # Correcting:
                                                       # Northbound for L2 is where L1 sends messages.
                                                       # Southbound for L2 is where L2 sends messages to L3.
        )
        # Re-evaluating bus connections for L2:
        # L2 (Strategy) receives goals from L1's southbound_bus_L1_L2.
        # L2 (Strategy) sends strategic objectives to L3 via its own southbound_bus_L2_L3.
        # L2 (Strategy) sends acknowledgements/status to L1 via L1's northbound_bus_L1_L2.

        self.strategy_layer = GlobalStrategyLayer(
            northbound_bus=self.southbound_bus_L1_L2, # Correct: L2's northbound IS L1's southbound
            southbound_bus=self.southbound_bus_L2_L3  # Correct: L2's southbound goes to L3
        )
        # And L1 needs to receive acks on its northbound from L2.
        # So L2 needs to be able to send to L1's northbound.
        # This means L1's northbound_bus (self.northbound_bus_L1_L2) is where L2 sends its northbound messages.
        # And L2's northbound_bus for its ACELayer init is where it receives from L1.

        # Let's simplify and be explicit with bus naming for clarity in ACELayer init
        # Bus for L1 to send to L2: L1_south_L2_north_bus
        # Bus for L2 to send to L1: L2_south_L1_north_bus (for acks, status)
        # Bus for L2 to send to L3: L2_south_L3_north_bus
        # Bus for L3 to send to L2: L3_south_L2_north_bus

        # L1 <-> L2 Buses
        self.L1_output_to_L2_input_bus = SouthboundBus()
        self.L2_output_to_L1_input_bus = NorthboundBus()
        # L2 <-> L3 Buses
        self.L2_output_to_L3_input_bus = SouthboundBus()
        self.L3_output_to_L2_input_bus = NorthboundBus()
        # L3 <-> L4 Buses
        self.L3_output_to_L4_input_bus = SouthboundBus()
        self.L4_output_to_L3_input_bus = NorthboundBus()
        # L4 <-> L5 Buses
        self.L4_output_to_L5_input_bus = SouthboundBus()
        self.L5_output_to_L4_input_bus = NorthboundBus()
        # L5 <-> L6 Buses
        self.L5_output_to_L6_input_bus = SouthboundBus()
        self.L6_output_to_L5_input_bus = NorthboundBus()
        # L6 -> Environment Bus
        self.L6_to_Environment_bus = SouthboundBus()

        # Layer Initializations
        self.aspirational_layer = AspirationalLayer(
            northbound_bus=self.L2_output_to_L1_input_bus,
            southbound_bus=self.L1_output_to_L2_input_bus,
            layer_name=f"{name}-L1-Aspirational"
        )
        self.strategy_layer = GlobalStrategyLayer(
            northbound_bus=self.L2_output_to_L1_input_bus,
            southbound_bus=self.L2_output_to_L3_input_bus,
            layer_name=f"{name}-L2-Strategy"
        )
        self.agent_model_layer = AgentModelLayer(
            northbound_bus=self.L3_output_to_L2_input_bus,
            southbound_bus=self.L3_output_to_L4_input_bus,
            layer_name=f"{name}-L3-AgentModel"
        )
        self.executive_layer = ExecutiveFunctionLayer(
            northbound_bus=self.L4_output_to_L3_input_bus,
            southbound_bus=self.L4_output_to_L5_input_bus,
            layer_name=f"{name}-L4-Executive"
        )
        self.cognitive_control_layer = CognitiveControlLayer(
            northbound_bus=self.L5_output_to_L4_input_bus,
            southbound_bus=self.L5_output_to_L6_input_bus,
            layer_name=f"{name}-L5-CognitiveControl"
        )
        self.task_prosecution_layer = TaskProsecutionLayer(
            northbound_bus=self.L6_output_to_L5_input_bus,
            southbound_bus=self.L6_to_Environment_bus,
            layer_name=f"{name}-L6-TaskProsecution"
        )

        # Initializing L1: It sends its constitutional goals southbound upon creation.
        initial_goals_from_L1 = self.L1_output_to_L2_input_bus.get_messages()
        print(f"Bot {self.name} init: L1 sent initial goals: {initial_goals_from_L1}")

        # L2 processes these initial goals.
        if initial_goals_from_L1:
            self.strategy_layer.process_northbound(initial_goals_from_L1)
            acks_from_L2 = self.L2_output_to_L1_input_bus.get_messages()
            if acks_from_L2:
                print(f"Bot {self.name} init: L1 processing acks from L2 for initial goals: {acks_from_L2}")
                self.aspirational_layer.process_southbound(acks_from_L2)

        initial_strategies_from_L2 = self.L2_output_to_L3_input_bus.get_messages()
        if initial_strategies_from_L2:
            print(f"Bot {self.name} init: L3 processing initial strategies from L2: {initial_strategies_from_L2}")
            self.agent_model_layer.process_northbound(initial_strategies_from_L2)
            initial_updates_from_L3 = self.L3_output_to_L2_input_bus.get_messages()
            if initial_updates_from_L3:
                print(f"Bot {self.name} init: L2 processing initial self-model updates from L3: {initial_updates_from_L3}")
                self.strategy_layer.process_southbound(initial_updates_from_L3)
            initial_tasks_from_L3 = self.L3_output_to_L4_input_bus.get_messages()
            if initial_tasks_from_L3:
                print(f"Bot {self.name} init: L4 processing initial tasks from L3: {initial_tasks_from_L3}")
                self.executive_layer.process_northbound(initial_tasks_from_L3)
                initial_updates_from_L4 = self.L4_output_to_L3_input_bus.get_messages()
                if initial_updates_from_L4:
                    print(f"Bot {self.name} init: L3 processing initial resource/risk updates from L4: {initial_updates_from_L4}")
                    self.agent_model_layer.process_southbound(initial_updates_from_L4)
                initial_plans_from_L4 = self.L4_output_to_L5_input_bus.get_messages()
                if initial_plans_from_L4:
                    print(f"Bot {self.name} init: L5 processing initial plans from L4: {initial_plans_from_L4}")
                    self.cognitive_control_layer.process_northbound(initial_plans_from_L4)
                    initial_updates_from_L5 = self.L5_output_to_L4_input_bus.get_messages()
                    if initial_updates_from_L5:
                        print(f"Bot {self.name} init: L4 processing initial status updates from L5: {initial_updates_from_L5}")
                        self.executive_layer.process_southbound(initial_updates_from_L5)
                    initial_task_for_L6 = self.L5_output_to_L6_input_bus.get_messages()
                    if initial_task_for_L6:
                        print(f"Bot {self.name} init: L6 processing initial task from L5: {initial_task_for_L6}")
                        self.task_prosecution_layer.process_northbound(initial_task_for_L6)
                        initial_status_from_L6 = self.L6_output_to_L5_input_bus.get_messages()
                        if initial_status_from_L6:
                            self.cognitive_control_layer.process_southbound(initial_status_from_L6)
                        self.L6_to_Environment_bus.get_messages() # Clear L6->Env bus


    def get_response(self, user_message: str) -> str:
        print(f"\n--- Bot {self.name} responding to user message: '{user_message}' ---")

        # 1. User message is given to GlobalStrategyLayer (L2) to update its environmental_context.
        #    (This is a simplification; in a full system, it might go to L3/AgentModel first)
        self.strategy_layer.environmental_context['current_conversation_topic'] = f"User query: {user_message[:50]}"
        self.strategy_layer.environmental_context['user_sentiment'] = 'neutral' # Reset or detect sentiment
        self.strategy_layer.environmental_context['session_history'].append({"user": user_message})
        print(f"[{self.strategy_layer.layer_name}] Updated context with user message: '{user_message}'. Current topic: {self.strategy_layer.environmental_context['current_conversation_topic']}")

        # 2. GlobalStrategyLayer (L2) sends a message northbound to AspirationalLayer (L1) for guidance.
        #    L2 uses its 'northbound_bus' (L2_output_to_L1_input_bus) to send this message.
        guidance_request_payload = {
            'action': 'request_guidance', # Standardized to 'action' key
            'user_message': user_message, # Pass the raw user message along
            'current_context': self.strategy_layer.environmental_context.copy()
        }
        print(f"[{self.strategy_layer.layer_name}] Sending guidance request to L1: {guidance_request_payload}")
        self.strategy_layer.send_northbound(guidance_request_payload)

        # 3. AspirationalLayer (L1) processes this northbound message from L2.
        #    Messages sent by L2 on L2_output_to_L1_input_bus are processed by L1's process_northbound.
        #    (Correction: L1's process_NORTHBOUND is for messages from L2 if L2 is considered "below" L1 in that interaction,
        #     or if L2 is sending a request that L1 processes as if it came from a lower layer.
        #     The ACE standard is: Layer N sends South, N+1 receives North. Layer N+1 sends North, N receives South.
        #     So, L2 sending North to L1 means L1's process_SOUTHBOUND should handle it.)

        # Corrected flow for L2 -> L1 request:
        # L2 sends on its northbound_bus (L2_output_to_L1_input_bus).
        # L1 must *receive* messages from this bus. L1's process_southbound is for messages from L2.
        messages_for_L1_from_L2 = self.L2_output_to_L1_input_bus.get_messages()
        if messages_for_L1_from_L2:
            print(f"[{self.aspirational_layer.layer_name}] Processing messages from L2 (requests): {messages_for_L1_from_L2}")
            self.aspirational_layer.process_southbound(messages_for_L1_from_L2) # L1's process_southbound for L2's NB messages

        # 4. AspirationalLayer (L1) sends goals/imperatives southbound.
        #    L1 uses its 'southbound_bus' (L1_output_to_L2_input_bus) to send these.
        goals_from_L1_for_L2 = self.L1_output_to_L2_input_bus.get_messages()
        if goals_from_L1_for_L2:
            print(f"[{self.aspirational_layer.layer_name}] Sent goals to L2: {goals_from_L1_for_L2}")
            # 5. GlobalStrategyLayer (L2) processes these southbound messages from L1.
            #    Messages sent by L1 on L1_output_to_L2_input_bus are processed by L2's process_northbound.
            print(f"[{self.strategy_layer.layer_name}] Processing goals from L1: {goals_from_L1_for_L2}")
            self.strategy_layer.process_northbound(goals_from_L1_for_L2)
        else:
            print(f"[{self.aspirational_layer.layer_name}] No new goals sent to L2.")


        # After L2 processes goals from L1, it might send acknowledgements back to L1.
        # These would be on L2_output_to_L1_input_bus, handled by L1.process_southbound in the next cycle if needed.
        acks_from_L2_for_L1 = self.L2_output_to_L1_input_bus.get_messages()
        if acks_from_L2_for_L1:
            print(f"[{self.strategy_layer.layer_name}] Sent acks to L1: {acks_from_L2_for_L1}")
            self.aspirational_layer.process_southbound(acks_from_L2_for_L1)


        # 6. GlobalStrategyLayer (L2) has now (potentially) formulated strategies and sent them southbound.
        #    These are on L2_output_to_L3_input_bus.
        strategies_for_L3 = self.L2_output_to_L3_input_bus.get_messages() # Get strategies from L2

        final_response_text = f"{self.name} (L6): No final output from L6." # Default if pipeline fails early

        if strategies_for_L3:
            print(f"[{self.agent_model_layer.layer_name}] Processing strategies from L2: {strategies_for_L3}")
            self.agent_model_layer.process_northbound(strategies_for_L3) # L3 processes strategies

            # L3 may send self-model updates/limitations northbound to L2.
            updates_from_L3_for_L2 = self.L3_output_to_L2_input_bus.get_messages()
            if updates_from_L3_for_L2:
                print(f"[{self.strategy_layer.layer_name}] Processing self-model/status updates from L3: {updates_from_L3_for_L2}")
                self.strategy_layer.process_southbound(updates_from_L3_for_L2)

            # L3 sends (refined) plans/tasks southbound to L4.
            tasks_for_L4 = self.L3_output_to_L4_input_bus.get_messages()
            if tasks_for_L4:
                print(f"[{self.executive_layer.layer_name}] Processing tasks from L3: {tasks_for_L4}")
                self.executive_layer.process_northbound(tasks_for_L4) # L4 processes tasks

                # L4 may send resource/risk updates northbound to L3.
                updates_from_L4_for_L3 = self.L4_output_to_L3_input_bus.get_messages()
                if updates_from_L4_for_L3:
                    print(f"[{self.agent_model_layer.layer_name}] Processing resource/risk/status updates from L4: {updates_from_L4_for_L3}")
                    self.agent_model_layer.process_southbound(updates_from_L4_for_L3)

                # L4 sends detailed execution plans southbound to L5.
                detailed_plans_for_L5 = self.L4_output_to_L5_input_bus.get_messages()
                if detailed_plans_for_L5:
                    print(f"[{self.cognitive_control_layer.layer_name}] Processing detailed plans from L4: {detailed_plans_for_L5}")
                    self.cognitive_control_layer.process_northbound(detailed_plans_for_L5) # L5 processes plans

                    # L5 may send status updates northbound to L4.
                    updates_from_L5_for_L4 = self.L5_output_to_L4_input_bus.get_messages()
                    if updates_from_L5_for_L4:
                        print(f"[{self.executive_layer.layer_name}] Processing status updates from L5: {updates_from_L5_for_L4}")
                        self.executive_layer.process_southbound(updates_from_L5_for_L4)

                    # L5 selects a task and sends it southbound to L6.
                    task_for_L6 = self.L5_output_to_L6_input_bus.get_messages()
                    if task_for_L6:
                        print(f"[{self.task_prosecution_layer.layer_name}] Processing task from L5: {task_for_L6}")
                        self.task_prosecution_layer.process_northbound(task_for_L6) # L6 "executes"

                        # L6 sends task completion status (including result) northbound to L5.
                        status_from_L6_for_L5 = self.L6_output_to_L5_input_bus.get_messages()
                        if status_from_L6_for_L5:
                            print(f"[{self.cognitive_control_layer.layer_name}] Processing status from L6: {status_from_L6_for_L5}")
                            self.cognitive_control_layer.process_southbound(status_from_L6_for_L5)

                            # Capture the actual response text from L6's result
                            last_l6_message = status_from_L6_for_L5[-1].payload
                            if last_l6_message.get("status") == "success":
                                final_response_text = str(last_l6_message.get("result", "L6: Success but no result text."))
                            else:
                                final_response_text = f"{self.name} (L6-Error): {last_l6_message.get('result', 'Processing error in L6.')}"
                        else:
                            final_response_text = f"{self.name} (L5): L6 did not report status."

                        # Simulate further northbound propagation of status for this cycle
                        updates_from_L5_for_L4_after_L6 = self.L5_output_to_L4_input_bus.get_messages()
                        if updates_from_L5_for_L4_after_L6: self.executive_layer.process_southbound(updates_from_L5_for_L4_after_L6)
                        updates_from_L4_for_L3_after_L5 = self.L4_output_to_L3_input_bus.get_messages()
                        if updates_from_L4_for_L3_after_L5: self.agent_model_layer.process_southbound(updates_from_L4_for_L3_after_L5)
                        updates_from_L3_for_L2_after_L4 = self.L3_output_to_L2_input_bus.get_messages()
                        if updates_from_L3_for_L2_after_L4: self.strategy_layer.process_southbound(updates_from_L3_for_L2_after_L4)
                        updates_from_L2_for_L1_after_L3 = self.L2_output_to_L1_input_bus.get_messages()
                        if updates_from_L2_for_L1_after_L3: self.aspirational_layer.process_southbound(updates_from_L2_for_L1_after_L3)

                        return final_response_text
                    else: # No task from L5 to L6
                        return f"{self.name} (L5): No task selected for L6."
                else: # No detailed plans from L4 to L5
                    return f"{self.name} (L4): No detailed execution plans generated for L5."
            else: # No tasks from L3 to L4
                 return f"{self.name} (L3): No tasks generated for L4."
        else: # No strategies from L2 to L3
             return f"{self.name} (L2): No strategies sent to L3 for '{user_message}'."


class ChatApp(App):
    def build(self):
        self.bots = []
        self.add_bot("Alpha")
        self.add_bot("Beta")
        self.root_widget = RootWidget()
        return self.root_widget

    def add_bot(self, name: str):
        bot = Bot(name)
        self.bots.append(bot)

    def send_message(self, message_text):
        if message_text.strip():
            chat_history = self.root_widget.ids.chat_history
            chat_history.text += f"You: {message_text}\n"
            for bot in self.bots:
                response = bot.get_response(message_text) # This now involves ACE
                chat_history.text += f"{response}\n" # Bot name is part of the response now
            self.root_widget.ids.message_input.text = ""

class RootWidget(BoxLayout):
    pass

if __name__ == '__main__':
    ChatApp().run()
