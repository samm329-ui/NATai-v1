import requests
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()
BASE_URL = "http://localhost:8000"

def print_welcome():
    console.clear()
    console.print(Panel.fit("[bold cyan]N.A.T. AI Assistant v1[/bold cyan]\n[cyan]Advanced AI with Memory & Real-time Search[/cyan]\n[cyan]Full Name: Natasha[/cyan]", border_style="cyan"))
    console.print()

def select_chatbot():
    console.print("[yellow]Select Chatbot Type:[/yellow]")
    console.print("  [1] General Chatbot (Memory-based)")
    console.print("  [2] Real-time Chatbot (Web Search)")
    while True:
        choice = console.input("[cyan]Enter choice (1/2): [/cyan]").strip()
        if choice == "1": return "general"
        elif choice == "2": return "realtime"
        else: console.print("[red]Invalid choice. Please enter 1 or 2[/red]")

def chat_loop(chat_type: str):
    session_id = None
    console.print(f"\n[green]Using {chat_type.upper()} chatbot[/green]")
    console.print("[dim]Type 'exit' to quit, 'new' to start new session[/dim]\n")
    while True:
        try:
            user_input = console.input("[bold cyan]> [/bold cyan]")
            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("[yellow]Goodbye![/yellow]")
                break
            if user_input.lower() == "new":
                session_id = None
                console.print("[dim]New session started[/dim]\n")
                continue
            if not user_input.strip():
                continue
            response = requests.post(f"{BASE_URL}/chat", json={"message": user_input, "session_id": session_id, "chat_type": chat_type})
            if response.status_code == 200:
                data = response.json()
                session_id = data["session_id"]
                console.print()
                md = Markdown(data["response"])
                console.print(md)
                if data.get("sources"):
                    console.print("\n[dim]Sources:[/dim]")
                    for source in data["sources"][:3]:
                        console.print(f"  [dim]- {source.get('title', 'Unknown')}[/dim]")
                console.print()
            else:
                console.print(f"[red]Error: {response.status_code}[/red]")
        except requests.exceptions.ConnectionError:
            console.print("[red]Error: Cannot connect to server. Make sure it's running![/red]")
            break
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

def show_status():
    try:
        response = requests.get(f"{BASE_URL}/system/status")
        if response.status_code == 200:
            data = response.json()
            console.print(Panel.fit(f"[bold]System Status[/bold]\n\nAI Name: N.A.T. (Natasha)\nModel: {data['model_name']}\nGroq API: {'Available' if data['groq_available'] else 'Not configured'}\nWeb Search: {'Available' if data['search_available'] else 'Not configured'}\nActive Sessions: {data['active_sessions']}\nVector Store: {data['vector_store']['document_count']} documents", border_style="green"))
        else:
            console.print(f"[red]Error: {response.status_code}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

def main():
    print_welcome()
    while True:
        console.print("\n[yellow]Menu:[/yellow]")
        console.print("  [1] Start Chat")
        console.print("  [2] System Status")
        console.print("  [3] Exit")
        choice = console.input("[cyan]Enter choice: [/cyan]").strip()
        if choice == "1":
            chat_type = select_chatbot()
            chat_loop(chat_type)
        elif choice == "2":
            show_status()
        elif choice == "3":
            console.print("[yellow]Goodbye![/yellow]")
            break
        else:
            console.print("[red]Invalid choice[/red]")

if __name__ == "__main__":
    main()
