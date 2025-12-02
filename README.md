# Business Strategy Analyzer

A web-based application that leverages AI to analyze business ideas and goals, providing strategic recommendations powered by GitHub Models.

## Features

- **Intuitive User Interface**: Clean, modern design for easy input of business ideas and goals
- **AI-Powered Analysis**: Uses advanced language models (GPT-4.1-mini) to provide strategic insights
- **Comprehensive Output**: Generates analysis covering:
  - Market opportunity assessment
  - Strategic recommendations
  - Implementation plan
  - Financial considerations
  - Next steps and success metrics

## Getting Started

### Prerequisites

- A modern web browser (Chrome, Firefox, Safari, Edge)
- (Optional) GitHub Personal Access Token for higher rate limits
  - Get yours from: https://github.com/settings/tokens

### Using the Application

1. **Open the Application**
   - Open `index.html` in your web browser

2. **Enter Your Information**
   - **Business Idea**: Describe your business idea, target market, and the problem it solves
   - **Business Goals**: Outline your goals and what you want to achieve

3. **Configure AI Settings** (Optional)
   - Provide a GitHub Personal Access Token for better rate limits
   - Without a token, the app uses the free tier (may have rate limits)

4. **Analyze**
   - Click "Analyze with AI" button
   - Wait for the AI to generate your strategic analysis
   - Review the comprehensive recommendations

5. **Clear**
   - Use "Clear" button to reset and start over

## API Integration

### Supported Models

- **GPT-4.1-mini** (Default): Balanced performance and cost for strategic analysis
- Other models can be configured by modifying `CONFIG.MODEL` in `app.js`

Available models:
- `gpt-4.1-mini` - Best for general use
- `gpt-4.1` - Better quality, lower latency
- `gpt-5-mini` - Latest lightweight model
- `gpt-4o-mini` - Cost-effective option

### Authentication

The application supports:
- **Free Tier**: No authentication required (limited rate limits)
- **GitHub Token**: Provide a Personal Access Token for higher rate limits and reliability

## File Structure

```
Stratigic-Platform/
├── index.html          # Main HTML interface
├── app.js              # JavaScript application logic
└── README.md           # This file
```

## Features Explained

### Market Opportunity Analysis
- Evaluates market size and growth potential
- Analyzes competitive landscape
- Identifies your unique value proposition

### Strategic Recommendations
- Identifies key success factors
- Assesses potential risks with mitigation strategies
- Highlights growth opportunities

### Implementation Plan
- Phase-based action items
- Key milestones to track
- Resource requirements

### Financial Considerations
- Estimates investment needs
- Suggests revenue models
- Projects break-even timeline

## Tips for Best Results

1. **Be Specific**: Provide detailed information about your business idea
2. **Clarify Goals**: Be clear about your short-term and long-term objectives
3. **Include Context**: Mention your target market, competitors, and unique advantages
4. **Review Carefully**: The AI-generated analysis is a starting point; validate with market research

## Error Handling

The application handles various error scenarios:
- **Invalid API Key**: Check your GitHub token
- **Rate Limit**: Try again later or provide an API key
- **Network Errors**: Check your internet connection
- **Missing Fields**: Fill in all required inputs

## Browser Compatibility

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Security Notes

- API keys are not stored locally
- All requests go directly to GitHub Models API
- No data is saved on any server
- Your business information stays private

## Troubleshooting

### "Network error" message
- Check your internet connection
- Ensure you can access https://models.github.ai

### "Rate limit exceeded"
- Wait a few minutes before trying again
- Provide a GitHub Personal Access Token for higher limits

### "Invalid API key"
- Verify your GitHub token is correct
- Ensure the token has the necessary permissions

## API Rate Limits

- **Free Tier**: ~60 requests per hour (without token)
- **With Token**: Varies based on GitHub plan (typically 1000+ per hour)

## Future Enhancements

- [ ] Save and export analysis reports
- [ ] Export analysis as PDF
- [ ] Multiple language support
- [ ] Business plan generation
- [ ] Financial projections
- [ ] Competitor analysis
- [ ] SWOT analysis visualization

## License

This project is open source and available under the MIT License.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Verify your network connection
3. Ensure you're using a supported browser
4. Try refreshing the page

## Disclaimer

This tool provides AI-generated analysis for informational purposes. Always conduct thorough market research and consult with business professionals before making strategic decisions.
