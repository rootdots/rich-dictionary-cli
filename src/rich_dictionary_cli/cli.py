from __future__ import annotations

import json
from typing import TypedDict, Annotated, TypeAlias

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.style import Style


# --- Type Definitions for API Response ---


class Definition(TypedDict):
    """Represents a single dictionary definition."""

    definition: str
    example: str | None


class Meaning(TypedDict):
    """Represents a meaning with part of speech and definitions."""

    partOfSpeech: str
    definitions: list[Definition]


class WordEntry(TypedDict):
    """Represents the top-level object for a single word lookup."""

    word: str
    phonetic: str | None
    meanings: list[Meaning]


# Define a TypeAlias for the complex return type (Python 3.10+)
APIResponse: TypeAlias = list[WordEntry] | None


# --- Global Instances ---

# Typer relies on rich, so we use the Console instance for output.
console = Console()

# 1. Initialize the Typer application instance globally
app = typer.Typer(
    name="rich-dictionary-cli",
    help="A rich, synchronous dictionary lookup tool.",  # Updated description
)


# --- Core Functionality ---


def fetch_word_data(word: str) -> APIResponse:
    """
    Fetches word data from the dictionary API synchronously.

    Parameters
    ----------
    word : str
        The word to look up.

    Returns
    -------
    APIResponse (list[WordEntry] | None)
        A list of WordEntry objects on success, otherwise None on error.

    """
    url: str = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

    # Use a timeout for robust network calls
    try:
        # Use synchronous httpx.Client
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url)
            _ = response.raise_for_status()

            # The JSON response is expected to match list[WordEntry]
            return response.json()

    except httpx.HTTPStatusError as e:
        # Handle 404 Not Found specifically, and other HTTP errors generally
        if e.response.status_code == 404:
            # Replaced markup with Text.assemble()
            console.print(
                Text.assemble(
                    Text("Error:", style="bold red"),
                    " Found no definition for '",
                    Text(word, style="yellow"),
                    "'.",
                ),
                style="red",
            )
        else:
            # Replaced markup with Text.assemble()
            console.print(
                Text.assemble(
                    Text(f"HTTP-error {e.response.status_code}:", style="bold red"),
                    " Could not fetch data.",
                ),
                style="red",
            )
        return None

    except httpx.RequestError as e:
        # Handle network-related issues (DNS, connection failures)
        console.print(
            Text.assemble(
                Text("Network error:", style="bold red"),
                f" An error occured with the connection to th API. ({e})",
            ),
            style="red",
        )
        return None

    except json.JSONDecodeError as exc:
        # Handle cases where the response is not valid JSON
        console.print(
            Text.assemble(
                Text("JSON-error:", style="bold red"),
                f" Error on decoding of API-response. ({exc})",
            ),
            style="red",
        )
        return None

    except Exception as e:
        # Catch any other unexpected errors
        console.print(
            Text.assemble(Text("Unexpected error:", style="bold red"), f" {e}"),
            style="red",
        )
        return None


def display_word_data(word: str, data: list[WordEntry]) -> None:
    """
    Displays the fetched definitions using rich.Panel for clear formatting.

    Parameters
    ----------
    word : str
        The original word searched.
    data : list[WordEntry]
        The list of word entries returned from the API.
    """
    word_upper: str = word.upper()

    # Replaced markup strings with Text.assemble() for Panel content and title
    word_text = Text.assemble(
        Text("WORD:", style="bold magenta"), " ", Text(word_upper, style="bold yellow")
    )
    title_text = Text("Dictionary search", style="bold green")

    console.print(
        Panel(word_text, border_style="cyan", title=title_text, title_align="left")
    )

    # Iterate over each top-level entry (sometimes words have multiple entries)
    for entry in data:
        phonetic: str | None = entry.get("phonetic")
        if phonetic:
            # Replaced markup with Text.assemble()
            console.print(Text.assemble("  Uttal: ", Text(phonetic, style="italic")))

        # Iterate over each meaning (part of speech)
        for meaning in entry.get("meanings", []):
            part_of_speech: str = meaning.get("partOfSpeech", "okänd ordklass")
            definitions: list[Definition] = meaning.get("definitions", [])

            if definitions:
                # Create a rich.Text buffer to build the panel content
                panel_content: Text = Text()

                # Add the part of speech as a header (already uses Style object)
                _ = panel_content.append(
                    f"{part_of_speech.capitalize()}\n",
                    style=Style(color="cyan", bold=True, underline=True),
                )

                # List the definitions
                for i, definition_data in enumerate(definitions, 1):
                    definition: str = definition_data.get(
                        "definition", "Ingen definition tillgänglig."
                    )
                    example: str | None = definition_data.get("example")

                    # 1. Add the definition text (already uses Style object)
                    _ = panel_content.append(f"\n{i}. ", style="bold white")
                    _ = panel_content.append(definition)

                    # 2. Add example, if available
                    if example:
                        # Display element in Swedish (Exempel)
                        _ = panel_content.append("\n    Exempel: ", style="dim")
                        _ = panel_content.append(f'"{example}"', style="italic")

                # Print the content inside a Panel
                # Replaced markup with Text object for Panel title
                panel_title = Text(part_of_speech.capitalize(), style="yellow")

                console.print(
                    Panel(
                        panel_content,
                        title=panel_title,
                        title_align="left",
                        border_style="green",
                        padding=(1, 2),
                    )
                )


# 2. The main command is now synchronous, eliminating async conflicts.
@app.command()
def main(
    # Use Annotated for cleaner Typer argument definition.
    word: Annotated[
        str, typer.Argument(help="The word to look up dictionary definitions for.")
    ],
) -> int:
    """
    Typer CLI entry point. Fetches and displays definitions for a given word.

    Parameters
    ----------
    word : str
        The word provided as a command-line argument.

    Returns
    -------
    int
        The exit code (0 for success, 1 for failure).
    """
    # Call the synchronous fetch function
    data: APIResponse = fetch_word_data(word)

    # Use match statement (Python 3.10+) for flow control
    match data:
        case None:
            # Error was handled and printed inside fetch_word_data
            return 1
        case list() as result if result:
            # Success: data is a non-empty list of definitions
            display_word_data(word, result)
            return 0
        case _:
            # Catches unexpected scenarios (e.g., an empty list or malformed data that wasn't None)

            # Replaced markup with Text.assemble() for safe printing in the final error message
            console.print(
                Text.assemble(
                    Text("Fel:", style="bold red"),
                    " Received an unexpected data-format for '",
                    Text(word, style="yellow"),
                    "'.",
                )
            )
            return 1


# 3. Define a synchronous wrapper function for entry point tools (like 'uv run')
def cli() -> None:
    """Synchronous entry point that runs the Typer application instance."""
    # This remains the same as the app is now fully synchronous.
    app()


if __name__ == "__main__":
    # When executed directly, run the synchronous wrapper
    cli()
