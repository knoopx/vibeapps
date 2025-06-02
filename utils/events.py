#!/usr/bin/env python3
import gi
gi.require_version('EDataServer', '1.2')
gi.require_version('ECal', '2.0')
from gi.repository import EDataServer, ECal, GLib
import sys
from datetime import datetime, timedelta

class EDSCalendarLister:

    def __init__(self):
        self.registry = None
        self.main_loop = None
        self.calendars = []

    def initialize_eds(self):
        try:
            self.registry = EDataServer.SourceRegistry.new_sync(None)
            return True
        except Exception as e:
            print(f'Failed to initialize EDS registry: {e}')
            return False

    def get_calendars(self):
        if not self.registry:
            return []
        calendars = []
        sources = self.registry.list_sources(EDataServer.SOURCE_EXTENSION_CALENDAR)
        for source in sources:
            if source.get_enabled():
                calendars.append({'uid': source.get_uid(), 'display_name': source.get_display_name(), 'source': source})
        return calendars

    def get_calendar_client(self, source):
        try:
            backend_name = None
            try:
                if hasattr(source, 'get_extension'):
                    backend = source.get_extension(EDataServer.SOURCE_EXTENSION_CALENDAR)
                    if backend and hasattr(backend, 'get_backend_name'):
                        backend_name = backend.get_backend_name()
            except:
                pass
            client = None
            if hasattr(ECal.Client, 'connect_sync'):
                try:
                    client = ECal.Client.connect_sync(source, ECal.ClientSourceType.EVENTS, 30, None)
                    if client:
                        client._backend_name = backend_name
                        return client
                except Exception as e:
                    print(f'connect_sync failed: {e}')
            if hasattr(ECal.Client, 'new'):
                try:
                    client = ECal.Client.new(source, ECal.ClientSourceType.EVENTS)
                    if client:
                        client.open_sync(None)
                        client._backend_name = backend_name
                        return client
                except Exception as e:
                    print(f'new+open_sync failed: {e}')
            if hasattr(ECal.Client, 'connect_sync'):
                try:
                    client = ECal.Client.connect_sync(source, ECal.ClientSourceType.EVENTS, None)
                    if client:
                        client._backend_name = backend_name
                        return client
                except Exception as e:
                    print(f'connect_sync without timeout failed: {e}')
            return None
        except Exception as e:
            print(f'Failed to open calendar client: {e}')
            return None

    def list_events(self, client, start_date=None, end_date=None):
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now() + timedelta(days=30)
        backend_name = getattr(client, '_backend_name', None)
        if backend_name == 'contacts':
            print(f'Detected contacts-based calendar, trying specialized methods...')
            events = self.list_contact_events(client, start_date, end_date)
            if events:
                return events
        try:
            events = []
            try:
                start_iso = start_date.strftime('%Y%m%dT%H%M%SZ')
                end_iso = end_date.strftime('%Y%m%dT%H%M%SZ')
                query = f'(occur-in-time-range? (make-time "{start_iso}") (make-time "{end_iso}"))'
                result = client.get_object_list_sync(query, None)
                if isinstance(result, tuple) and len(result) >= 2:
                    success, objects = (result[0], result[1])
                    if success and objects:
                        events = self.process_objects(objects)
                        if events:
                            return events
                elif result:
                    events = self.process_objects(result)
                    if events:
                        return events
            except Exception as e:
                print(f'ISO query failed: {e}')
            try:
                start_eds = start_date.strftime('%Y%m%dT000000Z')
                end_eds = end_date.strftime('%Y%m%dT235959Z')
                query = f'(occur-in-time-range? (make-time "{start_eds}") (make-time "{end_eds}"))'
                result = client.get_object_list_sync(query, None)
                if isinstance(result, tuple) and len(result) >= 2:
                    success, objects = (result[0], result[1])
                    if success and objects:
                        events = self.process_objects(objects)
                        if events:
                            return events
                elif result:
                    events = self.process_objects(result)
                    if events:
                        return events
            except Exception as e:
                print(f'EDS time format query failed: {e}')
            try:
                query = '#t'
                result = client.get_object_list_sync(query, None)
                objects = None
                if isinstance(result, tuple) and len(result) >= 2:
                    success, objects = (result[0], result[1])
                    if not success:
                        objects = None
                else:
                    objects = result
                if objects:
                    all_events = self.process_objects(objects)
                    events = []
                    for event in all_events:
                        if event.get('start_time') and start_date <= event['start_time'] <= end_date:
                            events.append(event)
                        elif not event.get('start_time'):
                            events.append(event)
                    return events
            except Exception as e:
                print(f'Get all query failed: {e}')
            return events
        except Exception as e:
            print(f'Failed to get events: {e}')
            return []

    def process_objects(self, objects):
        events = []
        if not objects:
            return events
        if not isinstance(objects, (list, tuple)):
            objects = [objects]
        for obj in objects:
            try:
                if obj is None or isinstance(obj, (bool, str, int)):
                    continue
                if isinstance(obj, list):
                    for sub_obj in obj:
                        component = self.extract_component(sub_obj)
                        if component:
                            event_info = self.parse_event_component(component)
                            if event_info:
                                events.append(event_info)
                    continue
                component = self.extract_component(obj)
                if component:
                    event_info = self.parse_event_component(component)
                    if event_info:
                        events.append(event_info)
                else:
                    basic_info = self.extract_basic_info(obj)
                    if basic_info:
                        events.append(basic_info)
            except Exception as e:
                print(f'Failed to process object: {e}')
                continue
        return events

    def extract_basic_info(self, obj):
        try:
            if obj is None or isinstance(obj, (bool, str, int, list)):
                return None
            event = {'uid': 'Unknown', 'summary': 'Unknown Event', 'description': '', 'location': '', 'start_time': None, 'end_time': None, 'all_day': False}
            for attr in ['uid', 'get_uid', 'id', 'get_id']:
                if hasattr(obj, attr):
                    try:
                        value = getattr(obj, attr)
                        if callable(value):
                            value = value()
                        if value:
                            event['uid'] = str(value)
                            break
                    except:
                        continue
            for attr in ['summary', 'get_summary', 'title', 'get_title', 'name', 'get_name']:
                if hasattr(obj, attr):
                    try:
                        value = getattr(obj, attr)
                        if callable(value):
                            value = value()
                        if value:
                            if hasattr(value, 'get_value'):
                                event['summary'] = value.get_value()
                            else:
                                event['summary'] = str(value)
                            break
                    except:
                        continue
            if event['uid'] != 'Unknown' or event['summary'] != 'Unknown Event':
                return event
            return None
        except Exception as e:
            print(f'Failed to extract basic info: {e}')
            return None

    def extract_component(self, obj):
        if obj is None:
            return None
        if hasattr(obj, 'get_uid') or hasattr(obj, 'get_summary'):
            return obj
        if hasattr(obj, 'get_component'):
            return obj.get_component()
        if hasattr(obj, 'get_icalcomponent'):
            return obj.get_icalcomponent()
        if hasattr(obj, 'as_string'):
            try:
                return None
            except:
                return None
        if hasattr(obj, 'get_vtype'):
            return obj
        return None

    def parse_event_component(self, component):
        try:
            if component is None:
                return None
            if isinstance(component, (bool, list, str, int)):
                return None
            if not hasattr(component, 'get_uid') and (not hasattr(component, 'get_summary')):
                if hasattr(component, 'get_component'):
                    component = component.get_component()
                elif hasattr(component, 'get_icalcomponent'):
                    component = component.get_icalcomponent()
                else:
                    return None
            if not component or not hasattr(component, 'get_uid'):
                return None
            event = {'uid': 'Unknown', 'summary': 'No Title', 'description': '', 'location': '', 'start_time': None, 'end_time': None, 'all_day': False}
            try:
                uid = component.get_uid()
                if uid:
                    event['uid'] = uid
            except:
                pass
            try:
                summary = component.get_summary()
                if summary:
                    if hasattr(summary, 'get_value'):
                        event['summary'] = summary.get_value()
                    else:
                        event['summary'] = str(summary)
            except:
                pass
            try:
                description = component.get_description()
                if description:
                    if hasattr(description, 'get_value'):
                        event['description'] = description.get_value()
                    else:
                        event['description'] = str(description)
            except:
                pass
            try:
                location = component.get_location()
                if location:
                    event['location'] = str(location)
            except:
                pass
            try:
                dtstart = component.get_dtstart()
                if dtstart:
                    event['start_time'] = self.ical_time_to_datetime(dtstart)
                    if dtstart and hasattr(dtstart, 'get_timezone'):
                        event['all_day'] = dtstart.get_timezone() is None and (not hasattr(dtstart, 'get_hour') or dtstart.get_hour() == 0)
            except:
                pass
            try:
                dtend = component.get_dtend()
                if dtend:
                    event['end_time'] = self.ical_time_to_datetime(dtend)
            except:
                pass
            return event
        except Exception as e:
            print(f'Failed to parse event: {e}')
            return None

    def ical_time_to_datetime(self, ical_time):
        if not ical_time:
            return None
        try:
            return datetime(ical_time.get_year(), ical_time.get_month(), ical_time.get_day(), ical_time.get_hour(), ical_time.get_minute(), ical_time.get_second())
        except:
            return None

    def format_event(self, event):
        lines = []
        lines.append(f"Title: {event['summary']}")
        lines.append(f"UID: {event['uid']}")
        if event['start_time']:
            if event['all_day']:
                lines.append(f"Date: {event['start_time'].strftime('%Y-%m-%d')} (All Day)")
            else:
                lines.append(f"Start: {event['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                if event['end_time']:
                    lines.append(f"End: {event['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        if event['location']:
            lines.append(f"Location: {event['location']}")
        if event['description']:
            lines.append(f"Description: {event['description'][:100]}{('...' if len(event['description']) > 100 else '')}")
        return '\n'.join(lines)

    def list_contact_events(self, client, start_date, end_date):
        events = []
        try:
            print('Trying contact-based calendar methods...')
            try:
                extended_start = start_date.replace(year=start_date.year - 10)
                extended_end = end_date.replace(year=end_date.year + 10)
                start_extended = extended_start.strftime('%Y%m%dT000000Z')
                end_extended = extended_end.strftime('%Y%m%dT235959Z')
                query = f'(occur-in-time-range? (make-time "{start_extended}") (make-time "{end_extended}"))'
                print(f'Trying extended time range query: {start_extended} to {end_extended}')
                result = client.get_object_list_sync(query, None)
                if isinstance(result, tuple) and len(result) >= 2:
                    success, objects = (result[0], result[1])
                    if success and objects:
                        print(f'Extended query returned {len(objects)} objects')
                        events = self.process_objects(objects)
                        if events:
                            return events
            except Exception as e:
                print(f'Extended time range query failed: {e}')
            try:
                query = '(has-recurrences? #t)'
                print('Trying recurrence query...')
                result = client.get_object_list_sync(query, None)
                if isinstance(result, tuple) and len(result) >= 2:
                    success, objects = (result[0], result[1])
                    if success and objects:
                        print(f'Recurrence query returned {len(objects)} objects')
                        events = self.process_objects(objects)
                        if events:
                            return events
            except Exception as e:
                print(f'Recurrence query failed: {e}')
            try:
                print('Trying to access underlying address book...')
                registry = client.get_registry() if hasattr(client, 'get_registry') else self.registry
                if registry:
                    book_sources = registry.list_sources(EDataServer.SOURCE_EXTENSION_ADDRESS_BOOK)
                    print(f'Found {len(book_sources)} address book sources')
                    for book_source in book_sources:
                        if book_source.get_enabled():
                            try:
                                print(f'Checking address book: {book_source.get_display_name()}')
                                book_events = self.extract_birthdays_from_addressbook(book_source, start_date, end_date)
                                if book_events:
                                    events.extend(book_events)
                            except Exception as e:
                                print(f'Failed to process address book {book_source.get_display_name()}: {e}')
            except Exception as e:
                print(f'Address book access failed: {e}')
            return events
        except Exception as e:
            print(f'Contact events listing failed: {e}')
            return []

    def extract_birthdays_from_addressbook(self, book_source, start_date, end_date):
        events = []
        try:
            gi.require_version('EBook', '1.2')
            from gi.repository import EBook
            book_client = None
            if hasattr(EBook.BookClient, 'connect_sync'):
                try:
                    book_client = EBook.BookClient.connect_sync(book_source, 30, None)
                except Exception as e:
                    print(f'Address book connect_sync failed: {e}')
            if not book_client and hasattr(EBook.BookClient, 'new'):
                try:
                    book_client = EBook.BookClient.new(book_source)
                    if book_client:
                        book_client.open_sync(None)
                except Exception as e:
                    print(f'Address book new+open failed: {e}')
            if not book_client:
                print('Could not create address book client')
                return events
            try:
                query = '#t'
                result = book_client.get_contacts_sync(query, None)
                contacts = None
                if isinstance(result, tuple) and len(result) >= 2:
                    success, contacts = (result[0], result[1])
                    if not success:
                        contacts = None
                else:
                    contacts = result
                if contacts:
                    print(f'Found {len(contacts)} contacts')
                    current_year = datetime.now().year
                    for contact in contacts:
                        try:
                            contact_events = self.extract_contact_dates(contact, current_year, start_date, end_date)
                            events.extend(contact_events)
                        except Exception as e:
                            print(f'Failed to process contact: {e}')
                            continue
                else:
                    print('No contacts found in address book')
            except Exception as e:
                print(f'Failed to get contacts: {e}')
            try:
                if hasattr(book_client, 'close'):
                    book_client.close()
            except:
                pass
        except Exception as e:
            print(f'Address book processing failed: {e}')
        return events

    def extract_contact_dates(self, contact, current_year, start_date, end_date):
        events = []
        try:
            name = 'Unknown Contact'
            if hasattr(contact, 'get_name_formatted') and contact.get_name_formatted():
                name = contact.get_name_formatted()
            elif hasattr(contact, 'get_full_name') and contact.get_full_name():
                name = contact.get_full_name()
            if hasattr(contact, 'get_birth_date'):
                try:
                    birth_date = contact.get_birth_date()
                    if birth_date:
                        for year in range(current_year - 1, current_year + 2):
                            try:
                                birthday = datetime(year, birth_date.get_month(), birth_date.get_day())
                                if start_date <= birthday <= end_date:
                                    age = year - birth_date.get_year() if birth_date.get_year() > 1900 else None
                                    summary = f"{name}'s Birthday"
                                    if age:
                                        summary += f' ({age} years old)'
                                    events.append({'uid': f'birthday-{contact.get_uid()}-{year}', 'summary': summary, 'description': f'Birthday of {name}', 'location': '', 'start_time': birthday, 'end_time': birthday, 'all_day': True})
                            except ValueError:
                                continue
                except Exception as e:
                    print(f'Failed to get birthday for {name}: {e}')
            if hasattr(contact, 'get_attributes'):
                try:
                    attrs = contact.get_attributes()
                    for attr in attrs:
                        if hasattr(attr, 'get_name') and hasattr(attr, 'get_value'):
                            attr_name = attr.get_name().lower()
                            if 'anniversary' in attr_name or 'wedding' in attr_name:
                                date_str = attr.get_value()
                                pass
                except Exception as e:
                    print(f'Failed to get anniversary for {name}: {e}')
        except Exception as e:
            print(f'Failed to extract dates from contact: {e}')
        return events

def main():
    lister = EDSCalendarLister()
    print('Initializing Evolution Data Server...')
    if not lister.initialize_eds():
        print('Failed to initialize EDS')
        return 1
    print('Getting available calendars...')
    calendars = lister.get_calendars()
    if not calendars:
        print('No calendars found or all calendars are disabled')
        return 1
    print(f'Found {len(calendars)} calendar(s):')
    for i, cal in enumerate(calendars):
        print(f"  {i + 1}. {cal['display_name']} ({cal['uid']})")
    print('\nListing events from all calendars...')
    total_events = 0
    for cal in calendars:
        print(f"\n{'=' * 60}")
        print(f"Calendar: {cal['display_name']}")
        print('=' * 60)
        client = lister.get_calendar_client(cal['source'])
        if not client:
            print('Failed to open calendar client')
            continue
        events = lister.list_events(client)
        if not events:
            print('No events found')
            print('Debugging: Trying to get raw objects...')
            try:
                result = client.get_object_list_sync('#t', None)
                print(f'Raw result type: {type(result)}')
                if isinstance(result, tuple):
                    success, objects = (result[0], result[1] if len(result) > 1 else None)
                    print(f'Success: {success}, Objects type: {type(objects)}')
                    if objects:
                        print(f"Objects length: {(len(objects) if hasattr(objects, '__len__') else 'N/A')}")
                        if hasattr(objects, '__iter__') and len(objects) > 0:
                            print('Sample objects:')
                            for i, obj in enumerate(objects[:3]):
                                print(f'  Object {i}: {type(obj)}')
                                obj_info = []
                                for attr_name in ['get_uid', 'uid', 'get_summary', 'summary', 'get_as_string', 'as_string']:
                                    if hasattr(obj, attr_name):
                                        try:
                                            attr = getattr(obj, attr_name)
                                            if callable(attr):
                                                value = attr()
                                                if value:
                                                    if hasattr(value, 'get_value'):
                                                        obj_info.append(f'{attr_name}: {value.get_value()}')
                                                    else:
                                                        obj_info.append(f'{attr_name}: {str(value)[:100]}')
                                            else:
                                                obj_info.append(f'{attr_name}: {str(attr)[:100]}')
                                        except Exception as e:
                                            obj_info.append(f'{attr_name}: ERROR - {e}')
                                if obj_info:
                                    for info in obj_info[:2]:
                                        print(f'    {info}')
                                else:
                                    print(f'    No accessible attributes found')
                                    attrs = [attr for attr in dir(obj) if not attr.startswith('_')][:5]
                                    print(f"    Available attributes: {', '.join(attrs)}")
                        else:
                            print('Objects list is empty')
                    else:
                        print('Objects is None or empty')
                else:
                    print(f"Direct result, length: {(len(result) if hasattr(result, '__len__') else 'N/A')}")
                    if hasattr(result, '__iter__') and len(result) > 0:
                        print('Processing direct result...')
                        processed = lister.process_objects(result)
                        if processed:
                            print(f'Found {len(processed)} events after processing direct result')
                            events = processed
            except Exception as e:
                print(f'Debug query failed: {e}')
            if not events:
                print('Trying alternative query methods...')
                print(f'Calendar source info:')
                try:
                    source_info = []
                    source_info.append(f"  Enabled: {cal['source'].get_enabled()}")
                    source_info.append(f"  Color: {(cal['source'].get_color() if hasattr(cal['source'], 'get_color') else 'N/A')}")
                    if hasattr(cal['source'], 'get_extension'):
                        try:
                            backend = cal['source'].get_extension(EDataServer.SOURCE_EXTENSION_CALENDAR)
                            if backend:
                                source_info.append(f"  Backend: {(backend.get_backend_name() if hasattr(backend, 'get_backend_name') else 'Unknown')}")
                                source_info.append(f"  Color (ext): {(backend.get_color() if hasattr(backend, 'get_color') else 'N/A')}")
                        except Exception as e:
                            source_info.append(f'  Backend info error: {e}')
                    for info in source_info:
                        print(info)
                except Exception as e:
                    print(f'  Error getting source info: {e}')
                try:
                    result = client.get_object_list_sync('', None)
                    if isinstance(result, tuple) and len(result) >= 2:
                        success, objects = (result[0], result[1])
                        if success and objects:
                            print(f'Empty query returned {len(objects)} objects')
                            processed = lister.process_objects(objects)
                            if processed:
                                events = processed
                except Exception as e:
                    print(f'Empty query failed: {e}')
                if not events:
                    query_attempts = ['(contains? "any" "")', '(= "any" "")', '(exists? "uid")', '(has-categories? #f)', '(not (has-categories? #t))', '#f']
                    for i, query in enumerate(query_attempts):
                        try:
                            print(f'Trying query {i + 1}: {query}')
                            result = client.get_object_list_sync(query, None)
                            if isinstance(result, tuple) and len(result) >= 2:
                                success, objects = (result[0], result[1])
                                if success and objects:
                                    print(f'Query {i + 1} returned {len(objects)} objects')
                                    processed = lister.process_objects(objects)
                                    if processed:
                                        events = processed
                                        break
                                else:
                                    print(f"Query {i + 1}: Success={success}, Objects={('empty' if not objects else len(objects))}")
                            else:
                                print(f"Query {i + 1}: Direct result with {(len(result) if hasattr(result, '__len__') else 'unknown')} items")
                        except Exception as e:
                            print(f'Query {i + 1} failed: {e}')
                if not events:
                    print('Trying client introspection...')
                    try:
                        client_methods = [method for method in dir(client) if not method.startswith('_')]
                        print(f"Available client methods: {', '.join(client_methods[:10])}...")
                        for method_name in ['get_object_list', 'get_objects', 'list_objects', 'get_all_objects']:
                            if hasattr(client, method_name):
                                try:
                                    print(f'Trying {method_name}...')
                                    method = getattr(client, method_name)
                                    if method_name in ['get_all_objects', 'list_objects']:
                                        result = method()
                                    else:
                                        result = method('#t')
                                    if result:
                                        print(f"{method_name} returned: {type(result)}, length: {(len(result) if hasattr(result, '__len__') else 'N/A')}")
                                        processed = lister.process_objects(result)
                                        if processed:
                                            events = processed
                                            break
                                except Exception as e:
                                    print(f'{method_name} failed: {e}')
                        if not events and hasattr(client, 'get_view'):
                            try:
                                print('Trying to get client view...')
                                view = client.get_view('#t')
                                if view:
                                    print(f'Got view: {type(view)}')
                                    if hasattr(view, 'start'):
                                        view.start()
                                        import time
                                        time.sleep(0.1)
                                    for view_method in ['get_objects', 'objects']:
                                        if hasattr(view, view_method):
                                            try:
                                                view_objects = getattr(view, view_method)()
                                                if view_objects:
                                                    print(f'View {view_method} returned {len(view_objects)} objects')
                                                    processed = lister.process_objects(view_objects)
                                                    if processed:
                                                        events = processed
                                                        break
                                            except Exception as e:
                                                print(f'View {view_method} failed: {e}')
                            except Exception as e:
                                print(f'View creation failed: {e}')
                    except Exception as e:
                        print(f'Client introspection failed: {e}')
            if not events and hasattr(client, '_backend_name') and (client._backend_name == 'contacts'):
                print('Final attempt: Contact-based calendar fallback...')
                contact_events = lister.list_contact_events(client, start_date=datetime.now() - timedelta(days=365), end_date=datetime.now() + timedelta(days=365))
                if contact_events:
                    events = contact_events
            if not events:
                print('This calendar appears to be genuinely empty or the events are in an unsupported format')
                continue
        print(f'Found {len(events)} event(s):')
        for i, event in enumerate(events, 1):
            print(f'\nEvent {i}:')
            print('-' * 40)
            print(lister.format_event(event))
        total_events += len(events)
        try:
            if hasattr(client, 'close'):
                client.close()
            elif hasattr(client, 'disconnect'):
                client.disconnect()
        except:
            pass
    print(f'\nTotal events found: {total_events}')
if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\nInterrupted by user')
        sys.exit(1)
    except Exception as e:
        print(f'Unexpected error: {e}')
        sys.exit(1)