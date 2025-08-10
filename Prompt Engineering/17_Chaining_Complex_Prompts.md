Title - Chaining complex prompts for stronger performance from LLM
    -  It is like breaking down a hard conversation with the AI into smaller, smarter stages — instead of dumping a huge complex task into one mega-prompt and hoping it gets everything right.
    - Why this works:

        - Cognitive Load Reduction → LLMs perform better when the task is broken into smaller, focused steps.

        - Progressive Context Building → Each step adds information or constraints to guide the next step.

        - Error Control → Mistakes can be fixed at intermediate steps before they snowball.
    - How to Build Chained Prompts
    The chain usually follows a 3 to 5 step structure:
        - Clarify
        - Decompose
        - Process
        - Integrate 
        - Refine
    
    - Let's say I will build Iron man 4 script in the current MCU timeline, Here's how my chain of prompts would look like
    
    - Step 1 — Clarify

    - Prompt:

    “I want to create a sci-fi movie script for Iron Man 4 in the MCU. Restate my goal in your own words and list any assumptions before starting.”

    Expected Output Pattern:

        Restatement of goal in simpler words

        Bullet list of assumptions (e.g., Tony Stark alive or dead, timeline placement, tone, target audience)
    
    Seeing the assumptions, I can further verify whichever I need or I don't want to include in my script and put prompt accordingly.

    - Step 2 — Decompose
    - Prompt:

        “Break this script project into major stages in logical order. For each stage, give 1–2 bullet points of what it covers.”

    - Expected Output Pattern:

        Stage 1: Concept & theme → bullets

        Stage 2: Characters → bullets

        Stage 3: Story arc → bullets

        Stage 4: Scene breakdown → bullets

        Stage 5: Dialogue writing → bullets
    
    
    - Step 3 — Process (Stage 1)
    - Prompt:

        “Let’s do Stage 1. Create 3 unique Iron Man 4 plot premises that fit within the MCU tone. Keep each premise under 3 sentences.”

    - Expected Output Pattern:

        Premise 1: Short description

        Premise 2: Short description

        Premise 3: Short description
    
    - Step 4 — Process (Stage 2)
    - Prompt:

        “Based on Premise 2, list the main characters (heroes, villains, supporting) with a short personality note for each.”

    Expected Output Pattern:

        Hero 1: personality trait

        Hero 2: personality trait

        Villain 1: personality trait

    Step 5 — Process (Stage 3)
    Prompt:

        “Now outline the full story arc for Premise 2 in 5 beats: beginning, rising action, climax, resolution, and epilogue.”

    Expected Output Pattern:

        Beat 1: 1–2 sentence summary

        Beat 2: …

        Beat 3: …

        Beat 4: …

        Beat 5: …

    - Step 6 — Process (Stage 4)
    Prompt:

        “Write a brief description of 3 key scenes from this arc that will be the most visually spectacular. 2–3 sentences per scene.”

    Expected Output Pattern:

        Scene 1: short description

        Scene 2: short description

        Scene 3: short description

    - Step 7 — Process (Stage 5)
    Prompt:

        “Write sample dialogue for Scene 1, between Iron Man and the main villain. Keep it snappy and under 8 lines.”

    Expected Output Pattern:

    Alternating character name + short line

    - Step 8 — Integrate
    Prompt:

        “Combine the story arc, key scenes, and sample dialogue into a single mini script draft (max 500 words). Keep the MCU tone consistent.”

    Expected Output Pattern:

        Short integrated draft with all parts blended

    - Step 9 — Refine
    Prompt:

        “Review the mini script for pacing, tone, and MCU authenticity. Suggest 3 changes that would make it feel even more like an official Marvel production.”

    Expected Output Pattern:

        Bullet list of improvement suggestions

[ Say the main benefits of it in 1-2 lines like summary to conclude.]