import openai
import os
import logging
from typing import Optional

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LLMInterface:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        # Using a placeholder if the Google base URL is specific and not set in env
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "YOUR_OPENAI_COMPATIBLE_BASE_URL_HERE")
        self.client = None

        if not self.api_key:
            logging.warning("OPENAI_API_KEY not found in environment variables or provided directly.")
            # raise ValueError("API key is required for LLMInterface.")
        if not self.base_url or self.base_url == "YOUR_OPENAI_COMPATIBLE_BASE_URL_HERE":
            logging.warning("OPENAI_BASE_URL not found in environment variables or provided directly, or is set to placeholder.")
            # raise ValueError("Base URL is required for LLMInterface.")

        if self.api_key and self.base_url and self.base_url != "YOUR_OPENAI_COMPATIBLE_BASE_URL_HERE":
            try:
                self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
                logging.info(f"LLMInterface initialized with base_url: {self.base_url}")
            except Exception as e:
                logging.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None # Ensure client is None if initialization fails
        else:
            logging.warning("LLMInterface not fully initialized due to missing API key or base URL.")

    def respond(self, system_prompt: str, user_prompt: str, model: str = "gemini-1.0-pro-latest") -> Optional[str]:
        if not self.client:
            logging.error("LLM client not initialized. Cannot make API call.")
            return "LLM not configured. Please check API key and base URL."

        try:
            logging.info(f"Sending request to LLM. Model: {model}, System Prompt: '{system_prompt[:50]}...', User Prompt: '{user_prompt[:50]}...'")
            completion = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            response_content = completion.choices[0].message.content
            logging.info(f"LLM response received. First choice: '{response_content[:50]}...'")
            return response_content
        except openai.APIConnectionError as e:
            logging.error(f"LLM API Connection Error: {e}")
            return "Error: Could not connect to LLM API."
        except openai.RateLimitError as e:
            logging.error(f"LLM API Rate Limit Error: {e}")
            return "Error: Rate limit exceeded for LLM API."
        except openai.APIStatusError as e:
            logging.error(f"LLM API Status Error (code {e.status_code}): {e.response}")
            return f"Error: LLM API returned status {e.status_code}."
        except openai.APIError as e:
            logging.error(f"Generic LLM API Error: {e}")
            return "Error: An API error occurred with the LLM."
        except Exception as e:
            logging.error(f"An unexpected error occurred during LLM API call: {e}")
            return "Error: An unexpected error occurred while contacting the LLM."

if __name__ == '__main__':
    # Example Usage (requires OPENAI_API_KEY and OPENAI_BASE_URL to be set in environment)
    # IMPORTANT: Replace "YOUR_OPENAI_COMPATIBLE_BASE_URL_HERE" with the actual base URL if testing locally.
    # The default base_url in the class init is a placeholder.

    # To test this locally, you might do:
    # export OPENAI_API_KEY="your_actual_api_key"
    # export OPENAI_BASE_URL="your_actual_base_url_for_gemini_or_other_openai_compatible_llm"

    print("Attempting to initialize LLMInterface...")
    # If you don't have env vars set, you can pass them directly for testing:
    # llm_interface = LLMInterface(api_key="your_key", base_url="your_url")
    llm_interface = LLMInterface()

    if llm_interface.client:
        print("LLMInterface initialized. Attempting a test call...")
        system_prompt_test = "You are a helpful assistant."
        user_prompt_test = "Hello, who are you?"

        # Using a very common, often free model for testing if possible, like a known small model.
        # For Gemini via Google AI Studio, "gemini-1.0-pro-latest" or "gemini-pro" is common.
        # Adjust model name as per your specific endpoint's model availability.
        # If your endpoint uses "gemini-2.0-flash", change it back.
        response = llm_interface.respond(system_prompt_test, user_prompt_test, model="gemini-1.0-pro-latest")

        if response:
            print(f"LLM Response: {response}")
        else:
            print("Failed to get a response from LLM.")
    else:
        print("LLMInterface client could not be initialized. Check API key and base URL.")
        print(f"Using API Key: {'Set' if llm_interface.api_key else 'Not Set'}")
        print(f"Using Base URL: {llm_interface.base_url}")

    print("\nTesting with missing configuration (should show warnings/errors):")
    llm_interface_no_config = LLMInterface(api_key="dummy_key_for_test_if_no_env_var", base_url="YOUR_OPENAI_COMPATIBLE_BASE_URL_HERE")
    response_no_config = llm_interface_no_config.respond("sys", "usr")
    print(f"Response with placeholder config: {response_no_config}")

    # Test with explicitly None key but valid URL (if URL is public and doesn't need key for some status check)
    # llm_interface_no_key = LLMInterface(api_key=None, base_url="https://api.example.com/v1") # Replace with a real public endpoint if testing this
    # response_no_key = llm_interface_no_key.respond("sys", "usr")
    # print(f"Response with no API key: {response_no_key}")

    # Test with key but no URL
    llm_interface_no_url = LLMInterface(api_key="dummy_key", base_url=None)
    response_no_url = llm_interface_no_url.respond("sys", "usr")
    print(f"Response with no Base URL: {response_no_url}")
