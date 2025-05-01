# Meme Generator

A powerful meme generation platform with both Twitter bot and web interface capabilities.

## Features

- Twitter bot for meme generation on demand
- Web interface for easy meme creation
- AI-powered caption generation
- Template matching and image understanding
- Support for custom templates

## Project Structure

```
memezap/
├── bot/                    # Twitter bot (V1)
├── webapp/                 # Memify.fun (V2)
├── ai_services/            # AI + ML related components
├── data/                   # Meme templates and examples
├── scripts/                # Utility or setup scripts
└── tests/                  # Unit & integration tests
```

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your API keys in `config.yaml`
4. Run the web application:
   ```bash
   python webapp/app.py
   ```
5. Run the Twitter bot:
   ```bash
   python bot/main.py
   ```

## Configuration

Edit `config.yaml` to set up:
- Twitter API credentials
- OpenAI API key
- Application settings
- Path configurations
- AI model settings

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License