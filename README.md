# XOS Wallet Client

A Python-based client for automating XOS wallet operations including login, check-in, and claiming rewards.

## Features

- 🔐 Multiple wallet support
- 📝 Daily check-in automation
- 🎲 Automatic draw claiming
- 💰 Points tracking
- 🔄 Proxy support
- 📊 Detailed progress tracking

## Installation

1. Clone the repository:
```bash
git clone https://github.com/himanshusaroha648/X_link.git
cd X_link
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

### Setting Up Private Keys

1. Create a `keys.txt` file in the project directory
2. Add your private keys (one per line)
3. Format: `0x...` or without `0x` prefix

Example `keys.txt`:
```
0x123...abc
0x456...def
```

### Running the Script

1. Single wallet mode:
```bash
python bot.py
```
Then select option 1 and enter your private key

2. Multiple wallets from keys.txt:
```bash
python bot.py --file
```

3. Multiple wallets from account.txt:
```bash
python bot.py --account
```

## Features

- **Multiple Wallet Support**: Process multiple wallets in sequence
- **Automatic Check-in**: Daily check-in automation
- **Draw System**: Automatic draw claiming
- **Points Tracking**: Track earned points
- **Proxy Support**: Optional proxy support for requests
- **Detailed Logging**: Comprehensive progress tracking

## Error Handling

- Rate limiting protection
- Automatic retries
- Detailed error logging
- Progress tracking

## Requirements

- Python 3.7+
- Required packages (see requirements.txt)

## Support

For issues and support, please create an issue in the repository.

## Disclaimer

This tool is for educational purposes only. Use responsibly and at your own risk.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
