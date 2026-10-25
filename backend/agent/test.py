from openai import OpenAI

client = OpenAI(
    api_key="cc_6enXCx6N988VPggRxPETMrK1Tx8IeLrICvpwddKEowcVG2xf",
    base_url="https://oxionai.com/v1",
)

response = client.chat.completions.create(
    model="gemma-2-2b",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)