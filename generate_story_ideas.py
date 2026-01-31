"""
Story Idea Batch Generator

Generates 30 story ideas using:
1. Multi-genre priming (sampled from pre-1970 genres)
2. Random words from tokenizer vocabulary (validated against dictionary)
3. LLM generation with priming context

Usage:
    python generate_story_ideas.py
"""

import random
import json
import os
from datetime import datetime
from openai import OpenAI
import tiktoken
import nltk

# Import genres
from genres import ALL_GENRES

# Configuration
MODEL = "anthropic/claude-opus-4.5"
NUM_IDEAS = 200
MAX_TOKEN_ID = 75000

# Load API key
with open("credential", "r") as f:
    OPENROUTER_API_KEY = f.read().strip()

# Initialize OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)


def call_llm(messages, model=MODEL, temperature=0.8, max_tokens=2000):
    """Call the LLM via OpenRouter."""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def prime_with_multi_genre_stories(n_genres=5):
    """
    Sample n random genres and ask the model to recall famous stories from each.
    This primes the model with diverse literary traditions before generation.
    """
    # Sample random genres
    sampled_genres = random.sample(ALL_GENRES, n_genres)

    # Randomly select a time period
    start_year = random.randrange(1910, 1971, 10)
    end_year = start_year + 50
    time_period = f"{start_year}-{end_year}"

    genre_list = "\n".join(f"- {genre}" for genre in sampled_genres)

    priming_prompt = f"""Let's warm up your creative circuits. Here are 5 randomly selected literary genres:
{genre_list}

For each genre, recall ONE famous story (published roughly around {time_period}) that exemplifies it.
For each story, explain in 1-2 sentences what narrative technique or structural choice made it memorable.
Focus on specific craft elements: how did the author create tension, develop character, and subvert expectations? What makes the ending particularly memorable or surprising?"""

    messages = [
        {"role": "system", "content": "You are a literary analyst with deep knowledge of storytelling across genres and eras."},
        {"role": "user", "content": priming_prompt}
    ]

    result = call_llm(messages, temperature=0.7)

    return {
        "genres": sampled_genres,
        "time_period": time_period,
        "priming_text": result
    }


def get_real_words_from_tokenizer(encoding, max_id=75000, min_len=4, max_len=15):
    """
    Extract tokens from LLM tokenizer, but only keep those that are
    real English words (validated against dictionary).

    This gives us words that are:
    1. Common enough to be in an LLM's vocabulary (actually used in text)
    2. Complete real words (not subword fragments)
    """
    # Download NLTK words corpus for dictionary validation
    nltk.download('words', quiet=True)
    from nltk.corpus import words as nltk_words

    # Build a set of valid English words for fast lookup
    english_dict = set(w.lower() for w in nltk_words.words())

    real_words = []
    for i in range(max_id):
        try:
            token = encoding.decode([i])
            # Tokens with leading space are word boundaries
            if token.startswith(" "):
                word = token.strip().lower()
                # Check: alphabetic, right length, AND in dictionary
                if (word.isalpha() and
                    min_len <= len(word) <= max_len and
                    word in english_dict):
                    real_words.append(word)
        except:
            continue
    return list(set(real_words))


def sample_random_words(vocab_words, n=20):
    """Sample n random words from vocabulary."""
    return random.sample(vocab_words, min(n, len(vocab_words)))


def generate_idea_from_words(words, priming_context):
    """Generate a story idea using the given words as creative seeds."""

    word_list = ", ".join(words)

    prompt = f"""Here are 20 randomly selected words:

{word_list}

Using at least 5 of these words as inspiration (not necessarily literally), generate a compelling story idea (3-4 sentences).
Before you generate, think about:
What is the core situation? What makes this story impossible to put down?
What is the primary form this story should take? (such as personal letter, journal, interview transcript, bureaucratic report, diplomatic correspondence, research log, notebook, company memo, obituary, field notes, pamphlet, ad, telegram, etc.)
Your response should include the story idea only. No intro, no outro. Be specific. Avoid generic tropes."""

    messages = [
        {"role": "system", "content": "You are a creative writing expert who just analyzed what makes great stories work."},
        {"role": "assistant", "content": priming_context},
        {"role": "user", "content": prompt}
    ]

    return call_llm(messages, temperature=0.9)


def main():
    print("=" * 60)
    print("Story Idea Batch Generator")
    print("=" * 60)

    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"generated_ideas/batch_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")

    # Step 1: Generate multi-genre priming
    print("\n[Step 1/3] Generating multi-genre priming context...")
    multi_genre_prime = prime_with_multi_genre_stories()
    print(f"  Genres: {multi_genre_prime['genres']}")
    print(f"  Time period: {multi_genre_prime['time_period']}")

    # Step 2: Build vocabulary
    print(f"\n[Step 2/3] Building vocabulary from tokenizer (max_id={MAX_TOKEN_ID})...")
    enc = tiktoken.get_encoding("cl100k_base")
    vocab_words = get_real_words_from_tokenizer(enc, max_id=MAX_TOKEN_ID)
    print(f"  Extracted {len(vocab_words)} real words")

    # Step 3: Generate ideas
    print(f"\n[Step 3/3] Generating {NUM_IDEAS} story ideas...")

    ideas = []
    all_ideas_content = f"# Story Ideas Batch\n\n"
    all_ideas_content += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    all_ideas_content += f"**Priming Genres:** {', '.join(multi_genre_prime['genres'])}\n"
    all_ideas_content += f"**Time Period:** {multi_genre_prime['time_period']}\n\n"
    all_ideas_content += "---\n\n"

    for i in range(NUM_IDEAS):
        print(f"  Generating idea {i+1}/{NUM_IDEAS}...", end=" ", flush=True)

        try:
            # Sample words and generate idea
            words = sample_random_words(vocab_words, n=20)
            idea = generate_idea_from_words(words, multi_genre_prime['priming_text'])

            # Store result
            idea_data = {
                "id": i + 1,
                "words": words,
                "idea": idea
            }
            ideas.append(idea_data)

            # Save individual file
            individual_content = f"# Story Idea {i+1:03d}\n\n"
            individual_content += f"**Words:** {', '.join(words)}\n\n"
            individual_content += "---\n\n"
            individual_content += idea

            with open(f"{output_dir}/idea_{i+1:03d}.md", "w") as f:
                f.write(individual_content)

            # Append to combined file
            all_ideas_content += f"## Idea {i+1:03d}\n\n"
            all_ideas_content += f"**Words:** {', '.join(words)}\n\n"
            all_ideas_content += idea
            all_ideas_content += "\n\n---\n\n"

            print("done")

        except Exception as e:
            print(f"error: {e}")
            ideas.append({
                "id": i + 1,
                "words": words if 'words' in dir() else [],
                "idea": f"ERROR: {str(e)}"
            })

    # Save combined file
    with open(f"{output_dir}/all_ideas.md", "w") as f:
        f.write(all_ideas_content)

    # Save metadata
    metadata = {
        "timestamp": timestamp,
        "num_ideas": NUM_IDEAS,
        "model": MODEL,
        "max_token_id": MAX_TOKEN_ID,
        "vocab_size": len(vocab_words),
        "priming": {
            "genres": multi_genre_prime['genres'],
            "time_period": multi_genre_prime['time_period'],
            "priming_text": multi_genre_prime['priming_text']
        },
        "ideas": ideas
    }

    with open(f"{output_dir}/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Complete! Generated {len([i for i in ideas if 'ERROR' not in i['idea']])} ideas")
    print(f"Output: {output_dir}/")
    print(f"  - all_ideas.md (combined)")
    print(f"  - idea_001.md to idea_{NUM_IDEAS:03d}.md (individual)")
    print(f"  - metadata.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
