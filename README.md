# AutoGluon Link Checker

AutoGluon Link Checker is a robust tool designed to crawl and identify broken links within AutoGluon's documentation. It operates seamlessly with GitHub Actions, providing daily reports for both stable and development documentation versions.

## Features

- **Crawling**: Checks links in doc.
- **Edge Case Handling**: Manages common issues like bot detection and DNS problems.
- **Reporting**: Generates comprehensive CSV reports highlighting broken links and their origins.
- **Configurable Allowlist**: Easily manage known false positives to reduce noise in reports.

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/autogluon-link-checker.git
   cd autogluon-link-checker
   ```

2. **Install Dependencies**:
   Ensure you have Python 3.9 installed. Then, install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the link checker script with the following command:

```bash
python get_broken_links.py
```


This will generate CSV files with broken links for both stable and development documentation.

## GitHub Actions Integration

The link checker is set up to run daily using GitHub Actions. The workflow is defined in `.github/workflows/broken_link_checker.yml`. It automatically commits and pushes CSV reports of broken links to the repository.

## Configuration

- **Allowed Domains**: Modify `ALLOWED_403_DOMAINS` in `get_broken_links.py` to add domains that are allowed to return 403 errors.
- **Ignored URLs**: Update `IGNORE_STRINGS_IN_URL` to skip specific URLs during the check.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For questions or feedback, please open an issue on GitHub or contact the maintainers directly.
