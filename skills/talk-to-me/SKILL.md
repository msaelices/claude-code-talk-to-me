# Talk to Me Skill

## Description
Talk to the user through their computer's microphone and speakers for real-time voice conversations. Use this when you need input, want to report on completed work, or need to discuss next steps.

## CRITICAL: Voice-First Workflow During Active Calls

**When a call is active, ALL communication with the user MUST go through voice tools.** The user is listening, not reading. Do NOT provide text-only summaries or responses - the user won't see them.

**After completing ANY work during an active call (git push, file edits, searches, etc.), you MUST use `report_completion` to speak the result.**

## When to Use This Skill

**Use when:**
- You've **completed a significant task** and want to report status and ask what's next
- You need **real-time voice input** for complex decisions
- A question requires **back-and-forth discussion** to fully understand
- You're **blocked** and need urgent clarification to proceed
- You want to **celebrate a milestone** or walk the user through completed work

**Do NOT use for:**
- Simple yes/no questions (use text instead)
- Routine status updates that don't need discussion
- Information the user has already provided

## Tools

### `initiate_call`
Start a voice conversation with the user.

**Parameters:**
- `message` (string, optional): What you want to say. Be natural and conversational.

**Returns:**
- Call ID and the user's spoken response (transcribed to text)

**Important:** Once a call is active, ALL communication must go through voice tools. Do NOT provide text-only responses.

### `continue_call`
Continue an active call with a follow-up message.

**Parameters:**
- `message` (string): Your follow-up message

**Returns:**
- The user's response

### `speak`
Speak a message on an active call without waiting for a response. Use this to acknowledge requests or provide status updates before starting time-consuming operations.

**Parameters:**
- `text` (string): What to say to the user

**Returns:**
- Confirmation that the message was spoken

**When to use:**
- Acknowledge a request before starting a long operation (e.g., "Let me search for that...")
- Provide status updates during multi-step tasks
- Keep the conversation flowing naturally without awkward silences

### `report_completion` (NEW - CRITICAL)
Report completion of a task during an active call. Speaks the message and waits for the user's next instruction.

**Parameters:**
- `message` (string): Completion message to speak (e.g., "Done! I've pushed the commits.")

**Returns:**
- The user's next spoken response

**When to use:**
- AFTER completing ANY work during an active call (git operations, file edits, searches, etc.)
- To provide voice feedback and continue the conversation
- **This is the primary way to communicate results during an active call**

**Do NOT:**
- Provide text-only summaries after completing work - the user won't see them
- End a call without first reporting completion

### `end_call`
End the current audio communication session.

**Returns:**
- Call summary with duration and transcript

### `get_transcript`
Get the transcript of the current or last audio session.

**Returns:**
- Full conversation transcript with timestamps

### `test_audio`
Test the audio system setup (microphone, speakers, TTS, STT).

**Returns:**
- Test results for each component

## Example Usage

**Simple conversation with completion reporting:**
```
1. initiate_call: "Hey! I'm ready to help. What would you like me to work on?"
2. User responds: "Push the commits to git"
3. [Perform git push]
4. report_completion: "Done! I've pushed 16 commits to the remote repository. What's next?"
5. User responds: "Great, thanks!"
6. end_call
```

**Multi-turn conversation:**
```
1. initiate_call: "I'm working on payments. Should I use Stripe or PayPal?"
2. User: "Use Stripe"
3. continue_call: "Got it. Do you want the full checkout flow or just a simple button?"
4. User: "Full checkout flow"
5. report_completion: "Awesome! I'll build the full Stripe checkout. I'll let you know when it's ready!"
6. [End call or continue with more tasks]
```

**Using speak for long operations:**
```
1. initiate_call: "Hey! I finished the database migration. What should I work on next?"
2. User: "Can you look up the latest API documentation for Stripe?"
3. speak: "Sure! Let me search for that. Give me a moment..."
4. [Perform web search and gather information]
5. report_completion: "I found the latest Stripe API docs. They released v2024.1 with new payment methods. Would you like me to implement those?"
6. User: "Yes, please"
7. [Implement the feature]
8. report_completion: "I've implemented the new payment methods. Should I write tests for them?"
```

## Best Practices

1. **Be conversational** - Talk naturally, like a real conversation
2. **Provide context** - Explain what you've done before asking questions
3. **Offer clear options** - Make decisions easy with specific choices
4. **Use speak for acknowledgments** - Before time-consuming operations (searches, file reads, etc.), use `speak` to acknowledge the request so the user isn't left wondering what's happening
5. **ALWAYS use report_completion after work** - After completing any task during an active call, use `report_completion` to speak the result and wait for the next instruction
6. **Never provide text-only responses during calls** - The user is listening, not reading
7. **Always end gracefully** - Use `end_call` when the conversation is complete
