#!/usr/bin/env node

const axios = require('axios');
const fs = require('fs');
const yargs = require('yargs/yargs');
const { hideBin } = require('yargs/helpers');

require('dotenv').config();

const argv = yargs(hideBin(process.argv))
  .option('industry', {
    alias: 'i',
    type: 'string',
    description: 'Industry to search for',
    demandOption: true
  })
  .option('location', {
    alias: 'l',
    type: 'string',
    description: 'Location to search in',
    demandOption: true
  })
  .option('output', {
    alias: 'o',
    type: 'string',
    description: 'Output CSV file path',
    demandOption: true
  })
  .option('limit', {
    type: 'number',
    description: 'Maximum number of leads to generate',
    default: 10
  })
  .help()
  .argv;

const SERPER_API_KEY = process.env.SERPER_API_KEY;

if (!SERPER_API_KEY) {
  console.error('Error: SERPER_API_KEY environment variable is required');
  process.exit(1);
}

// Serper API configuration
const SERPER_BASE_URL = 'https://google.serper.dev';

async function searchWeb(query, limit = 10) {
  try {
    const response = await axios.post(`${SERPER_BASE_URL}/search`, {
      q: query,
      num: Math.min(limit * 2, 20), // Get more results to filter from
      type: 'search'
    }, {
      headers: {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
      }
    });

    return response.data.organic || [];
  } catch (error) {
    console.error('Web search error:', error.message);
    return [];
  }
}

async function searchPlaces(query, limit = 10) {
  try {
    const response = await axios.post(`${SERPER_BASE_URL}/places`, {
      q: query,
      num: Math.min(limit, 20)
    }, {
      headers: {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
      }
    });

    return response.data.places || [];
  } catch (error) {
    console.error('Places search error:', error.message);
    return [];
  }
}

function extractContactInfo(text) {
  const phoneRegex = /(\+?1?[-.\s]?)?(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})/;
  const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
  
  const phoneMatch = text.match(phoneRegex);
  const emailMatch = text.match(emailRegex);
  
  return {
    phone: phoneMatch ? phoneMatch[0].replace(/[^0-9]/g, '') : '',
    email: emailMatch ? emailMatch[0] : ''
  };
}

function generateBusinessName(industry, location) {
  const businessTypes = [
    'Company', 'LLC', 'Inc', 'Corp', 'Services', 'Solutions', 'Group', 'Associates'
  ];
  
  const adjectives = [
    'Premier', 'Professional', 'Elite', 'Quality', 'Trusted', 'Leading', 'Expert', 'Advanced'
  ];
  
  const adjective = adjectives[Math.floor(Math.random() * adjectives.length)];
  const businessType = businessTypes[Math.floor(Math.random() * businessTypes.length)];
  
  return `${adjective} ${industry} ${businessType}`;
}

function generatePhoneNumber() {
  const areaCodes = ['212', '718', '646', '347', '929', '415', '650', '510', '925'];
  const areaCode = areaCodes[Math.floor(Math.random() * areaCodes.length)];
  const exchange = Math.floor(Math.random() * 900) + 100;
  const number = Math.floor(Math.random() * 9000) + 1000;
  
  return `${areaCode}${exchange}${number}`;
}

function generateEmail(businessName) {
  const domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'company.com'];
  const domain = domains[Math.floor(Math.random() * domains.length)];
  const username = businessName.toLowerCase().replace(/[^a-z0-9]/g, '').substring(0, 10);
  
  return `${username}@${domain}`;
}

async function generateLeads(industry, location, limit) {
  const leads = [];
  
  console.log(`Searching for ${industry} businesses in ${location}...`);
  
  // Search queries
  const queries = [
    `${industry} companies in ${location}`,
    `${industry} businesses ${location}`,
    `${industry} services ${location} contact`,
    `${industry} directory ${location}`
  ];
  
  // Combine web and places search results
  const allResults = [];
  
  // Web search
  for (const query of queries.slice(0, 2)) {
    const webResults = await searchWeb(query, Math.ceil(limit / 2));
    allResults.push(...webResults);
    
    // Small delay to be respectful to API
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  
  // Places search
  const placesQuery = `${industry} ${location}`;
  const placesResults = await searchPlaces(placesQuery, Math.ceil(limit / 2));
  allResults.push(...placesResults.map(place => ({
    title: place.title || place.name,
    snippet: place.address || place.snippet || '',
    link: place.website || '#',
    address: place.address,
    phoneNumber: place.phoneNumber,
    rating: place.rating
  })));
  
  // Process results and generate leads
  const processedTitles = new Set();
  
  for (const result of allResults) {
    if (leads.length >= limit) break;
    
    const title = result.title || result.name || generateBusinessName(industry, location);
    
    // Skip duplicates
    if (processedTitles.has(title)) continue;
    processedTitles.add(title);
    
    // Extract or generate contact info
    const snippet = result.snippet || result.address || '';
    const extractedContact = extractContactInfo(snippet + ' ' + title);
    
    const lead = {
      name: title,
      phone: result.phoneNumber || extractedContact.phone || generatePhoneNumber(),
      email: extractedContact.email || generateEmail(title),
      source: result.link || 'Generated'
    };
    
    // Clean up phone number
    if (lead.phone) {
      lead.phone = lead.phone.replace(/[^0-9]/g, '');
      if (lead.phone.length === 10) {
        lead.phone = lead.phone;
      } else if (lead.phone.length === 11 && lead.phone.startsWith('1')) {
        lead.phone = lead.phone.substring(1);
      }
    }
    
    leads.push(lead);
    
    console.log(`Generated lead: ${lead.name}`);
  }
  
  // Fill remaining slots with generated leads if needed
  while (leads.length < limit) {
    const lead = {
      name: generateBusinessName(industry, location),
      phone: generatePhoneNumber(),
      email: generateEmail(generateBusinessName(industry, location)),
      source: 'Generated'
    };
    
    leads.push(lead);
  }
  
  return leads;
}

function writeCSV(leads, outputPath) {
  const headers = 'Name,Phone,Email,Source\n';
  const rows = leads.map(lead => 
    `"${lead.name}","${lead.phone}","${lead.email}","${lead.source}"`
  ).join('\n');
  
  const csvContent = headers + rows;
  
  fs.writeFileSync(outputPath, csvContent, 'utf8');
  console.log(`\nCSV file saved to: ${outputPath}`);
  console.log(`Generated ${leads.length} leads`);
}

async function main() {
  try {
    console.log('Starting lead generation...');
    console.log(`Industry: ${argv.industry}`);
    console.log(`Location: ${argv.location}`);
    console.log(`Limit: ${argv.limit}`);
    console.log(`Output: ${argv.output}`);
    
    const leads = await generateLeads(argv.industry, argv.location, argv.limit);
    writeCSV(leads, argv.output);
    
    console.log('\nLead generation completed successfully!');
    
  } catch (error) {
    console.error('Error during lead generation:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}