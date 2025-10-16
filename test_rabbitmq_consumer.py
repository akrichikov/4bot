#!/usr/bin/env python3
"""
Test RabbitMQ Consumer for 4bot
Verifies messages can be consumed from the queues
"""

import json
import os
from dotenv import load_dotenv
from rabbitmq_manager import RabbitMQManager, BotMessage
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime

# Load environment
load_dotenv()

console = Console()


def test_consumer():
    """Test consuming messages from RabbitMQ"""
    console.print(Panel.fit(
        "[bold cyan]RabbitMQ Consumer Test[/bold cyan]\n"
        "[dim]Listening for messages on 4bot queues[/dim]",
        border_style="cyan"
    ))

    manager = RabbitMQManager()
    manager.connect()

    # Message handler
    def handle_message(message: BotMessage):
        """Handle incoming messages"""
        console.print(f"\n[green]📬 Received Message[/green]")

        table = Table(show_header=False, box=None)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("ID", message.message_id)
        table.add_row("Type", message.message_type)
        table.add_row("Source", message.source)
        table.add_row("Timestamp", message.timestamp)
        table.add_row("Data", json.dumps(message.data, indent=2))

        console.print(table)

    # Register handlers
    manager.register_handler("test", handle_message)
    manager.register_handler("notification", handle_message)
    manager.register_handler("command", handle_message)

    console.print("[yellow]👂 Listening on 4bot_request queue...[/yellow]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        # Start consuming
        manager.consume_requests()

    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️ Stopping consumer...[/yellow]")
        manager.stop_consuming()
        manager.close()
        console.print("[green]✅ Consumer stopped[/green]")


def test_publisher():
    """Test publishing messages to RabbitMQ"""
    console.print(Panel.fit(
        "[bold cyan]RabbitMQ Publisher Test[/bold cyan]\n"
        "[dim]Sending test messages to queues[/dim]",
        border_style="cyan"
    ))

    manager = RabbitMQManager()
    manager.connect()

    # Send various message types
    test_messages = [
        {
            "routing_key": "4bot.request.command",
            "message": BotMessage(
                message_id=f"test_{datetime.now().timestamp()}",
                message_type="command",
                timestamp=datetime.now().isoformat(),
                source="test",
                data={"command": "status", "parameters": {}}
            )
        },
        {
            "routing_key": "4bot.response.notification",
            "message": BotMessage(
                message_id=f"test_{datetime.now().timestamp()}",
                message_type="notification",
                timestamp=datetime.now().isoformat(),
                source="test",
                data={
                    "type": "follow",
                    "from_user": "test_user",
                    "timestamp": datetime.now().isoformat()
                }
            )
        }
    ]

    for msg_config in test_messages:
        success = manager.publish_message(
            message=msg_config["message"],
            routing_key=msg_config["routing_key"]
        )

        if success:
            console.print(f"[green]✅ Published to {msg_config['routing_key']}[/green]")
        else:
            console.print(f"[red]❌ Failed to publish to {msg_config['routing_key']}[/red]")

    manager.close()
    console.print("\n[green]✅ Publisher test complete[/green]")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "publish":
        test_publisher()
    else:
        console.print("[cyan]Starting consumer test...[/cyan]")
        console.print("[dim]Run 'python test_rabbitmq_consumer.py publish' in another terminal to send test messages[/dim]\n")
        test_consumer()