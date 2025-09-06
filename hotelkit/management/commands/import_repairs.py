from django.core.management.base import BaseCommand
from hotelkit.utils import parse_excel_file, import_repair_requests_from_dataframe


class Command(BaseCommand):
    help = 'Import repair requests from Excel file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the Excel file')
        parser.add_argument('--update', action='store_true', help='Update existing records')

    def handle(self, *args, **options):
        file_path = options['file_path']
        
        try:
            self.stdout.write(f'Parsing Excel file: {file_path}')
            df = parse_excel_file(file_path)
            self.stdout.write(f'Parsed {len(df)} rows')
            
            self.stdout.write('Importing data...')
            result = import_repair_requests_from_dataframe(df)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Import completed:\n'
                    f'  - Imported: {result["imported"]}\n'
                    f'  - Updated: {result["updated"]}\n'
                    f'  - Errors: {len(result["errors"])}'
                )
            )
            
            if result['errors']:
                self.stdout.write(self.style.WARNING('Errors encountered:'))
                for error in result['errors'][:10]:  # Show first 10 errors
                    self.stdout.write(f'  - {error}')
                if len(result['errors']) > 10:
                    self.stdout.write(f'  ... and {len(result["errors"]) - 10} more errors')
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Import failed: {str(e)}')
            )
