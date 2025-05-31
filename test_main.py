import unittest
from main import Bot, ChatApp # Assuming ChatApp might be needed for full setup, not strictly for Bot alone
from ace_framework import (
    AspirationalLayer, GlobalStrategyLayer, AgentModelLayer,
    ExecutiveFunctionLayer, CognitiveControlLayer, TaskProsecutionLayer,
    Message, NorthboundBus, SouthboundBus
)

class TestBotInitialization(unittest.TestCase):
    def test_bot_creation_and_ace_layer_initialization(self):
        bot = Bot(name="TestBot")
        self.assertIsInstance(bot.aspirational_layer, AspirationalLayer)
        self.assertEqual(bot.aspirational_layer.layer_name, "TestBot-L1-Aspirational")

        self.assertIsInstance(bot.strategy_layer, GlobalStrategyLayer)
        self.assertEqual(bot.strategy_layer.layer_name, "TestBot-L2-Strategy")

        self.assertIsInstance(bot.agent_model_layer, AgentModelLayer)
        self.assertEqual(bot.agent_model_layer.layer_name, "TestBot-L3-AgentModel")

        self.assertIsInstance(bot.executive_layer, ExecutiveFunctionLayer)
        self.assertEqual(bot.executive_layer.layer_name, "TestBot-L4-Executive")

        self.assertIsInstance(bot.cognitive_control_layer, CognitiveControlLayer)
        self.assertEqual(bot.cognitive_control_layer.layer_name, "TestBot-L5-CognitiveControl")

        self.assertIsInstance(bot.task_prosecution_layer, TaskProsecutionLayer)
        self.assertEqual(bot.task_prosecution_layer.layer_name, "TestBot-L6-TaskProsecution")

class TestACEFlow(unittest.TestCase):
    def test_single_message_journey(self):
        bot = Bot(name="FlowBot")

        # Store initial memory/history lengths
        initial_l2_session_history_len = len(bot.strategy_layer.environmental_context['session_history'])
        initial_l3_episodic_memory_len = len(bot.agent_model_layer.episodic_memory)

        response = bot.get_response("hello there general kenobi")
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)
        print(f"\nTestACEFlow - Bot Response to 'hello there general kenobi': {response}")

        # Check that some interaction was recorded (simplistic check)
        self.assertTrue(len(bot.strategy_layer.environmental_context['session_history']) > initial_l2_session_history_len)
        self.assertTrue(len(bot.agent_model_layer.episodic_memory) > initial_l3_episodic_memory_len)

        # Example of peeking into a bus (L6 to L5) - requires bus not to be cleared by other parts of init/flow
        # This is fragile and depends on execution order.
        # For more robust testing, buses might need a "peek" or "log" feature for tests.
        # Or layers could log their received/sent messages to a testable buffer.

        # Let's test another response to see if it processes
        response_2 = bot.get_response("what is the weather like")
        self.assertIsInstance(response_2, str)
        self.assertTrue(len(response_2) > 0)
        print(f"TestACEFlow - Bot Response to 'what is the weather like': {response_2}")


class TestTaskProsecutionLayer(unittest.TestCase):
    def setUp(self):
        self.north_bus = NorthboundBus()
        self.south_bus = SouthboundBus() # Dummy southbound for L6
        self.task_prosecution_layer = TaskProsecutionLayer(
            northbound_bus=self.north_bus,
            southbound_bus=self.south_bus,
            layer_name="TestL6"
        )

    def test_greet_task_execution(self):
        # L5 would typically provide a more abstract instruction, but L6 tries to parse strings too
        task_instruction_payload = {
            "task_id": "test_greet_01",
            # Forcing a string that the L6 heuristic should pick up for greeting
            "instruction": "Step 1: Initialize resources for 'Execute: greet user TestUser'",
            "parent_l4_task_id": "l4_parent_greet_task"
        }
        message_from_l5 = Message(source_layer='L5', payload=task_instruction_payload)

        self.task_prosecution_layer.process_northbound([message_from_l5])

        l6_northbound_messages = self.north_bus.get_messages()
        self.assertEqual(len(l6_northbound_messages), 1)

        l6_output = l6_northbound_messages[0].payload
        self.assertEqual(l6_output['status'], 'success')
        self.assertEqual(l6_output['task_id'], task_instruction_payload['task_id'])
        self.assertEqual(l6_output['result'], "Hello! How can I help you today?") # Based on L6's heuristic

    def test_structured_greet_task_execution(self):
        task_instruction_payload = {
            "task_id": "test_greet_structured_02",
            "instruction": {"action": "greet_user", "details": {"user_name": "Tester"}},
            "parent_l4_task_id": "l4_parent_greet_task_structured"
        }
        message_from_l5 = Message(source_layer='L5', payload=task_instruction_payload)

        self.task_prosecution_layer.process_northbound([message_from_l5])

        l6_northbound_messages = self.north_bus.get_messages()
        self.assertEqual(len(l6_northbound_messages), 1)

        l6_output = l6_northbound_messages[0].payload
        self.assertEqual(l6_output['status'], 'success')
        self.assertEqual(l6_output['task_id'], task_instruction_payload['task_id'])
        self.assertEqual(l6_output['result'], "Hello Tester!")

    def test_unknown_structured_action(self):
        task_instruction_payload = {
            "task_id": "test_unknown_03",
            "instruction": {"action": "fly_to_moon", "details": {}},
            "parent_l4_task_id": "l4_parent_unknown_task"
        }
        message_from_l5 = Message(source_layer='L5', payload=task_instruction_payload)

        self.task_prosecution_layer.process_northbound([message_from_l5])

        l6_northbound_messages = self.north_bus.get_messages()
        self.assertEqual(len(l6_northbound_messages), 1)

        l6_output = l6_northbound_messages[0].payload
        self.assertEqual(l6_output['status'], 'failure')
        self.assertEqual(l6_output['task_id'], task_instruction_payload['task_id'])
        self.assertIn("don't know how to execute it yet", l6_output['result'])
        self.assertEqual(l6_output['details'], "Unknown action type")

if __name__ == '__main__':
    unittest.main()
