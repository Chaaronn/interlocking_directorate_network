import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import your functions here
from scraper import search_ch, adv_search_ch, get_persons_with_control_info, get_active_sig_persons_from_name, get_entity_information, constuct_ch_link, recusive_get_company_tree_from_sigs

class TestCompanyHouseAPI(unittest.TestCase):

    @patch('requests.Session.get')
    def test_search_ch(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'items': [{'company_number': '12345678'}]}
        mock_get.return_value = mock_response
        
        response = search_ch("Test Company")
        self.assertIsNotNone(response)
        self.assertIn('items', response)
        self.assertEqual(response['items'][0]['company_number'], '12345678')

    @patch('requests.Session.get')
    def test_adv_search_ch(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'items': [{'company_number': '12345678'}]}
        mock_get.return_value = mock_response
        
        response = adv_search_ch("Test", "Exclude", ["active"], ["62020"])
        self.assertIsNotNone(response)
        self.assertIn('items', response)
        self.assertEqual(response['items'][0]['company_number'], '12345678')

    @patch('requests.Session.get')
    def test_get_persons_with_control_info(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'active_count': 1, 'items': [{'name': 'John Doe'}]}
        mock_get.return_value = mock_response
        
        response = get_persons_with_control_info('/company/12345678')
        self.assertIsNotNone(response)
        self.assertIn('active_count', response)
        self.assertEqual(response['active_count'], 1)

    @patch('requests.Session.get')
    def test_get_active_sig_persons_from_name(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            {'items': [{'links': {'self': '/company/12345678'}}]},
            {'active_count': 1, 'items': [{'name': 'John Doe'}]}
        ]
        mock_get.return_value = mock_response
        
        response = get_active_sig_persons_from_name("Test Company")
        self.assertIsNotNone(response)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0]['name'], 'John Doe')

    @patch('requests.Session.get')
    def test_get_entity_information(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'company_name': 'Test Company'}
        mock_get.return_value = mock_response
        
        response = get_entity_information('/company/12345678')
        self.assertIsNotNone(response)
        self.assertIn('company_name', response)
        self.assertEqual(response['company_name'], 'Test Company')

    def test_constuct_ch_link(self):
        result = constuct_ch_link('12345678')
        expected_url = 'find-and-update.company-information.service.gov.uk/company/12345678/'
        self.assertEqual(result, expected_url)

    @patch('requests.Session.get')
    def test_recursive_get_company_tree_from_sigs(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            {'items': [{'links': {'self': '/company/12345678'}, 'company_number': '12345678', 'title': 'Test Company'}]},
            {'active_count': '1', 'items': [{'name': 'John Doe', 'etag': 'abc', 'notified_on': '2020-01-01', 'ceased_on': '2022-01-01', 'links': {'self': '/psc/123'}}]},
            {'company_name': 'Test Entity'}
        ]
        mock_get.return_value = mock_response
        
        response = recusive_get_company_tree_from_sigs("Test Company", 2019, 2023)
        self.assertIsNotNone(response)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0]['name'], 'John Doe')
        self.assertEqual(response[0]['company_name'], 'Test Company')

if __name__ == '__main__':
    unittest.main()
