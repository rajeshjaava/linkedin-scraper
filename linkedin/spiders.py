# -*- coding: utf-8 -*-

import unicodecsv as csv
import scrapy
import json
import sys

from collections import defaultdict
from linkedin.items import LinkedinItem

SERVER = 'https://www.linkedin.com'

# Strings which are treated as separators of position and company. Everything
# to the left of any of these strings is interpreted as the position,
# everything to the right as the company.
POSITION_COMPANY_SEPARATORS = [u' at ', u' bei ', u' ve společnosti ']

class LinkedinSpider(scrapy.Spider):
    name = "linkedin"

    def __init__(self, access_token, keywords, output_file):
        super(LinkedinSpider, self).__init__()

        # Construct URL from keywords
        self.url = '{0}/search/results/index/?keywords={1}'.format(
            SERVER, keywords
        )

        # Construct cookie from access token
        self.cookies = {'li_at': access_token}

        self.output_file = output_file

    def start_requests(self):
        yield scrapy.Request(
            url=self.url, cookies=self.cookies, callback=self.parse
        )

    def parse(self, response):
        """ Parse a LinkedIn search results page """
        selector = '//code[last()-2]/text()'
        miniprofile = 'com.linkedin.voyager.identity.shared.MiniProfile'
        search_profile = 'com.linkedin.voyager.search.SearchProfile'

        results = defaultdict(dict)
        for block in response.selector.xpath(selector).extract():
            json_data = json.loads(block)
            for item in json_data.get('included', {}):
                if item.get('$type') == miniprofile:
                    self.parse_miniprofile(item, results)
                elif item.get('$type') == search_profile:
                    self.parse_searchprofile(item, results)

        # Convert all complete results to ScraPy items
        items = []
        for result in results.values():
            if all(field in result for field in LinkedinItem.fields.keys()):
                items.append(LinkedinItem(result))

        # Write items to CSV file
        self.write_results(items)

    def parse_miniprofile(self, item, results):
        """ Parse MiniProfile item and add it to results """
        urn = item.get('objectUrn')
        occupation = item.get('occupation')
        for separator in POSITION_COMPANY_SEPARATORS:
            if separator in occupation:
                position, company = occupation.split(separator, 1)
                break
        else:
            position, company = occupation, None

        results[urn].update({
            'first_name': item.get('firstName') or '',
            'last_name': item.get('lastName') or '',
            'position': position or '',
            'company': company or '',
        })

    def parse_searchprofile(self, item, results):
        """ Parse SearchProfile item and add it to results """
        urn = item.get('backendUrn')
        location = item.get('location')
        try:
            city, country = location.rsplit(', ', 1)
        except ValueError:
            city, country = None, location

        results[urn].update({
            'city': city or '',
            'country': country or '',
        })

    def write_results(self, items):
        """ Write results to CSV file """
        with open(self.output_file, 'wb') as csv_file:
            csv_writer = csv.writer(csv_file, encoding='utf-8')

            # Write header
            csv_writer.writerow([
                'First name', 'Last name', 'Position', 'Company', 'City',
                'Country',
            ])

            # Write items
            for item in items:
                csv_writer.writerow([
                    item.get('first_name'),
                    item.get('last_name'),
                    item.get('position'),
                    item.get('company'),
                    item.get('city'),
                    item.get('country'),
                ])
