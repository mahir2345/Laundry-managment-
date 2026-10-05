from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.gridlayout import GridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.dialog import MDDialog
from kivy.core.window import Window
from kivy.utils import platform
from kivy.graphics import Color, Rectangle
from datetime import datetime
import os


class PhoneScreen(Screen):
    """Screen for phone number input"""
    def __init__(self, controller, **kwargs):
        super().__init__(**kwargs)
        self.controller = controller
        self.build_ui()
        
        # Load the last used phone number when the screen is created
        self.load_last_phone_number()
    
    def build_ui(self):
        # We don't need to build UI here as it's defined in the KV file
        # Just create a reference to the phone input field for use in our methods
        pass
        
    def on_kv_post(self, base_widget):
        # This method is called after the KV file is loaded
        # Get a reference to the phone input field
        self.phone_input = self.ids.phone_input
        self.phone_input.bind(text=self.on_phone_changed)
        
        # Initialize the history layout if it exists in the KV file
        if hasattr(self.ids, 'history_layout'):
            self.history_layout = self.ids.history_layout
        else:
            # Create a fallback history layout if not in KV
            self.history_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
            self.history_layout.bind(minimum_height=self.history_layout.setter('height'))
        
        # We'll use the history_layout from the KV file
        # This will be initialized in on_kv_post
        
    def go_to_history(self, *args):
        """Navigate to history screen"""
        # Pass the current phone number to the history screen
        phone = self.phone_input.text.strip()
        self.manager.get_screen('history').set_phone_number(phone)
        self.manager.current = 'history'
    
    def on_phone_changed(self, instance, value):
        """Called when phone number input changes"""
        if not value or len(value) < 10:  # Reset UI if phone number is cleared or too short
            self.highlight_returning_customer(False)
            self.history_layout.clear_widgets()
            return
            
        # Only search when we have a reasonable phone number
        if len(value) >= 10:  
            # Update history display
            self.update_history(value)
            
            # Check if this phone number has existing orders
            # If it does, enable auto-continue functionality
            orders = self.controller.get_customer_orders(value)
            if orders and len(orders) > 0:
                # Add visual indicator that this is a returning customer
                self.highlight_returning_customer(True)
            else:
                # Reset UI if no orders found
                self.highlight_returning_customer(False)
    
    def update_history(self, phone):
        """Update the service history for the given phone number"""
        # Clear previous history
        self.history_layout.clear_widgets()
        
        # Get customer orders
        orders = self.controller.get_customer_orders(phone)
        
        if not orders:
            no_history = MDLabel(
                text='No service history found',
                size_hint_y=None,
                height=40,
                halign='center'
            )
            self.history_layout.add_widget(no_history)
            return
        
        # Add each order to the history list
        for order in orders:
            # The order is now a dictionary, not a tuple
            order_id = order['order_id']
            created_at = order['created_at']
            total = order['total_amount']
            
            # Convert timestamp string to datetime if needed
            if isinstance(created_at, str):
                try:
                    created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    try:
                        created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        created_at = datetime.now()  # Fallback
            
            # Format date
            date_str = created_at.strftime('%Y-%m-%d %H:%M') if isinstance(created_at, datetime) else str(created_at)
            
            # Create order item widget
            item = MDBoxLayout(size_hint_y=None, height=60, orientation='vertical', padding=5)
            item.add_widget(MDLabel(
                text=f"Order ID: {order_id}",
                size_hint_y=0.5,
                halign='left',
                theme_text_color="Primary"
            ))
            item.add_widget(MDLabel(
                text=f"Date: {date_str} | Total: TK {total:.2f}",
                size_hint_y=0.5,
                halign='left',
                theme_text_color="Secondary"
            ))
            
            # Add a separator
            separator = MDBoxLayout(size_hint_y=None, height=1)
            with separator.canvas.before:
                Color(0.7, 0.7, 0.7, 1)
                Rectangle(pos=separator.pos, size=(400, 1))
            
            self.history_layout.add_widget(item)
            self.history_layout.add_widget(separator)
    
    def start_order(self, *args):
        phone = self.phone_input.text.strip()
        if not phone:
            self.show_error("Please enter a phone number")
            return
        
        order = self.controller.start_new_order(phone)
        if order:
            self.manager.current = 'items'
        else:
            self.show_error("Failed to create order")
    
    def highlight_returning_customer(self, is_returning):
        """Highlight the phone input if this is a returning customer"""
        if is_returning:
            # Change the input field style to indicate a returning customer
            self.phone_input.helper_text = "Returning Customer"
            self.phone_input.helper_text_mode = "persistent"
            self.phone_input.helper_text_color = [0.2, 0.8, 0.2, 1]  # Green
            
            # Update the Start Order button if it exists in the KV file
            if hasattr(self.ids, 'start_button'):
                self.ids.start_button.text = 'Continue with Order'
                self.ids.start_button.md_bg_color = [0.2, 0.8, 0.2, 1]  # Green
            
            # Add auto-continue functionality
            # When the user enters a phone number with existing history,
            # automatically start a new order after a short delay
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.auto_continue(), 1.5)  # 1.5 second delay
        else:
            # Reset to default styles
            self.phone_input.helper_text = "Format: +8801XXXXXXXXX"
            self.phone_input.helper_text_mode = "on_focus"
            self.phone_input.helper_text_color = self.theme_cls.primary_color if hasattr(self, 'theme_cls') else [0.2, 0.6, 0.8, 1]
            
            # Reset the Start Order button if it exists
            if hasattr(self.ids, 'start_button'):
                self.ids.start_button.text = 'Start Order'
                self.ids.start_button.md_bg_color = self.theme_cls.primary_color if hasattr(self, 'theme_cls') else [0.2, 0.6, 0.8, 1]
    
    def auto_continue(self):
        """Automatically continue with the order if this is a returning customer"""
        phone = self.phone_input.text.strip()
        if phone and len(phone) >= 10:
            # Verify this phone has orders before continuing
            orders = self.controller.get_customer_orders(phone)
            if not orders or len(orders) == 0:
                return
                
            # Show a dialog to inform the user
            dialog = MDDialog(
                title='Welcome Back!',
                text=f'Continuing with phone number {phone}\n\nYou have {len(orders)} previous order(s)',
                size_hint=(0.8, 0.4),
                buttons=[
                    MDFlatButton(
                        text="Cancel",
                        on_release=lambda x: dialog.dismiss()
                    ),
                    MDRaisedButton(
                        text="Continue",
                        on_release=lambda x: self.process_continue(dialog, phone)
                    ),
                ],
            )
            dialog.open()
    
    def process_continue(self, dialog, phone):
        """Process the continuation after dialog confirmation"""
        try:
            dialog.dismiss()
            # Call auto_continue with the phone number
            success, result = self.controller.auto_continue(phone)
            if success:
                self.manager.current = 'items'
            else:
                self.show_error(result)
        except Exception as e:
            print(f"Error in auto_continue: {e}")
            self.show_error(f"An error occurred: {str(e)}")
    
    def load_last_phone_number(self):
        """Load the last used phone number from the database and set it in the input field"""
        # We're removing the auto-loading of the last phone number
        # to prevent showing a fixed number when the app starts
        # If you want to re-enable this feature, uncomment the code below
        
        # last_phone = self.controller.get_last_phone_number()
        # if last_phone:
        #     # Set the phone number in the input field
        #     self.phone_input.text = last_phone
        #     # This will trigger on_phone_changed which will update the history
            # and highlight if it's a returning customer
    
    def show_error(self, message):
        dialog = MDDialog(
            title='Error',
            text=message,
            size_hint=(0.8, 0.3)
        )
        dialog.open()


class ItemsScreen(Screen):
    """Screen for adding items"""
    def __init__(self, controller=None, **kwargs):
        super().__init__(**kwargs)
        self.controller = controller
        self.service = controller.service if controller else None
        self.item_widgets = []
    
    def on_kv_post(self, base_widget):
        # Initialize widgets after KV file has been processed
        self.item_name = self.ids.item_name
        self.quantity = self.ids.quantity
        self.service_type = self.ids.service_type
        self.rate = self.ids.rate
        self.total_label = self.ids.total_label
        self.item_box = self.ids.item_box
        
        # Set values for spinners if controller is available
        if hasattr(self, 'controller') and self.controller:
            self.item_name.values = self.controller.get_item_name_types()
            self.service_type.values = self.controller.get_service_types()
    
    def add_item(self, instance):
        name = self.item_name.text
        quantity = self.quantity.text.strip()
        service = self.service_type.text
        rate = self.rate.text.strip()
        
        if not all([name, quantity, service != 'Select Service', rate]):
            self.show_error("Please fill all fields")
            return
        
        try:
            qty = int(quantity)
            rt = float(rate)
            if qty <= 0 or rt <= 0:
                self.show_error("Quantity and rate must be positive")
                return
                
            success = self.controller.add_item_to_order(name, qty, service, rt)
            if success:
                self.update_items_list()
                self.clear_form()
            else:
                self.show_error("Failed to add item")
        except ValueError:
            self.show_error("Invalid quantity or rate")
    
    def update_items_list(self):
        self.item_box.clear_widgets()
        self.item_widgets = []
        
        current_order = self.controller.service.current_order
        if current_order:
            for i, item in enumerate(current_order.items):
                item_layout = MDBoxLayout(size_hint_y=None, height=40, spacing=5)
                
                # Item details
                item_text = f"{item.name} - {item.service_type} x{item.quantity} = TK {item.subtotal:.2f}"
                item_label = MDLabel(text=item_text, size_hint_x=0.8, theme_text_color="Primary")
                item_layout.add_widget(item_label)
                
                # Remove button
                remove_btn = MDRaisedButton(
                    text='X',
                    size_hint_x=0.2,
                    md_bg_color=(0.8, 0.2, 0.2, 1)
                )
                remove_btn.bind(on_press=lambda x, idx=i: self.remove_item(idx))
                item_layout.add_widget(remove_btn)
                
                self.item_box.add_widget(item_layout)
                self.item_widgets.append(item_layout)
            
            # Update total
            total = current_order.get_total()
            self.total_label.text = f'Total: TK {total:.2f}'
    
    def remove_item(self, index):
        self.controller.remove_item_from_order(index)
        self.update_items_list()
    
    def clear_form(self):
        self.item_name.text = 'Select Item'
        self.quantity.text = ''
        self.service_type.text = 'Select Service'
        self.rate.text = ''
    
    def proceed(self, instance):
        current_order = self.controller.service.current_order
        if current_order and current_order.items:
            self.manager.current = 'receipt'
        else:
            self.show_error("Please add at least one item")
    
    def go_back(self, instance):
        self.manager.current = 'phone'
    
    def show_error(self, message):
        popup = Popup(
            title='Error',
            content=Label(text=message),
            size_hint=(0.8, 0.3)
        )
        popup.open()


class ReceiptScreen(Screen):
    """Screen for receipt generation options"""
    def __init__(self, controller, **kwargs):
        super().__init__(**kwargs)
        self.controller = controller
        self.build_ui()
        
    def generate_pdf(self, *args):
        """Generate PDF receipt and send to printer"""
        self.process_receipt('pdf')
    
    def build_ui(self):
        layout = MDBoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Title
        title = MDLabel(
            text='Order Summary',
            size_hint_y=0.1,
            font_size='22sp',
            bold=True,
            halign='center'
        )
        layout.add_widget(title)
        
        # Order details
        scroll = MDScrollView(size_hint_y=0.5)
        self.details_label = MDLabel(
            text='',
            size_hint_y=None,
            markup=True,
            halign='left'
        )
        self.details_label.bind(
            texture_size=lambda *x: setattr(self.details_label, 'height', self.details_label.texture_size[1])
        )
        scroll.add_widget(self.details_label)
        layout.add_widget(scroll)
        
        # Receipt options
        options_layout = MDBoxLayout(orientation='vertical', size_hint_y=0.3, spacing=10)
        
        receipt_label = MDLabel(text='Choose Receipt Option:', size_hint_y=0.3, halign='center')
        options_layout.add_widget(receipt_label)
        
        btn_layout = MDBoxLayout(spacing=10, size_hint_y=0.7)
        
        pdf_btn = MDRaisedButton(
            text='Generate PDF',
            md_bg_color=(0.2, 0.6, 0.8, 1),
            size_hint_x=0.5,
            pos_hint={"center_x": 0.5}
        )
        pdf_btn.bind(on_press=lambda x: self.process_receipt('pdf'))
        btn_layout.add_widget(pdf_btn)
        
        sms_btn = MDRaisedButton(
            text='Send SMS',
            md_bg_color=(0.2, 0.7, 0.3, 1),
            size_hint_x=0.5,
            pos_hint={"center_x": 0.5}
        )
        sms_btn.bind(on_press=lambda x: self.process_receipt('sms'))
        btn_layout.add_widget(sms_btn)
        
        options_layout.add_widget(btn_layout)
        layout.add_widget(options_layout)
        
        # Back button
        back_btn = MDRaisedButton(
            text='Back to Items',
            size_hint_y=0.1,
            size_hint_x=1,
            md_bg_color=(0.8, 0.3, 0.3, 1)
        )
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'items'))
        layout.add_widget(back_btn)
        
        self.add_widget(layout)
    
    def on_enter(self):
        """Called when screen is displayed"""
        self.update_details()
    
    def update_details(self):
        current_order = self.controller.service.current_order
        if current_order:
            details = f"[b]Order ID:[/b] {current_order.order_id}\n"
            details += f"[b]Customer Phone:[/b] {current_order.customer_phone}\n"
            details += f"[b]Date:[/b] {current_order.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            details += "[b]Items:[/b]\n"
            
            for item in current_order.items:
                details += f"• {item.name} - {item.service_type}\n"
                details += f"  Qty: {item.quantity} × Rate: {item.rate} = [b]TK {item.subtotal:.2f}[/b]\n"
            
            details += f"\n[b][color=008800]TOTAL: TK {current_order.get_total():.2f}[/color][/b]"
            
            self.details_label.text = details
    
    def process_receipt(self, receipt_type):
        success, message = self.controller.process_receipt(receipt_type)
        
        popup_title = 'Success' if success else 'Error'
        
        if success:
            if receipt_type == 'pdf':
                # Show receipt printer message
                info = "Sending to receipt printer..."
                
                # Create a popup to show the printing status
                content = BoxLayout(orientation='vertical', padding=10, spacing=10)
                content.add_widget(Label(text=info, halign='center'))
                
                popup = Popup(
                    title='Printing Receipt',
                    content=content,
                    size_hint=(0.8, 0.3)
                )
                popup.open()
                
                # Simulate printing process (in a real app, this would connect to a printer)
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: self.finish_printing(popup), 2)
            else:  # SMS
                popup = Popup(
                    title='SMS Sent',
                    content=Label(text=f"SMS sent successfully to {self.controller.service.current_order.customer_phone}"),
                    size_hint=(0.8, 0.3)
                )
                popup.open()
                
                # Go back to phone input screen for a new order
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'phone'), 2)
        else:
            # Show error
            popup = Popup(
                title='Error',
                content=Label(text=message),
                size_hint=(0.8, 0.3)
            )
            popup.open()
            
    def finish_printing(self, popup):
        """Called when printing is complete"""
        popup.dismiss()
        
        # Show success message
        success_popup = Popup(
            title='Success',
            content=Label(text="Receipt printed successfully!"),
            size_hint=(0.8, 0.3)
        )
        success_popup.open()
        
        # Go back to phone input screen for a new order
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'phone'), 2)


class HistoryScreen(Screen):
    """Screen for viewing order history"""
    def __init__(self, controller, **kwargs):
        super().__init__(**kwargs)
        self.controller = controller
        self.phone_number = None
        self.build_ui()
    
    def build_ui(self):
        layout = MDBoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Title
        title = MDLabel(
            text='Order History',
            size_hint_y=0.1,
            font_size='22sp',
            bold=True,
            halign='center'
        )
        layout.add_widget(title)
        
        # Phone number display
        self.phone_label = MDLabel(
            text='Phone: ',
            size_hint_y=0.1,
            font_size='16sp',
            halign='center'
        )
        layout.add_widget(self.phone_label)
        
        # Scrollable history list
        scroll = MDScrollView(size_hint_y=0.7)
        self.history_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.history_layout.bind(minimum_height=self.history_layout.setter('height'))
        scroll.add_widget(self.history_layout)
        layout.add_widget(scroll)
        
        # Back button
        back_btn = MDRaisedButton(
            text='Back',
            size_hint_y=0.1,
            size_hint_x=1,
            md_bg_color=(0.8, 0.3, 0.3, 1)
        )
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'phone'))
        layout.add_widget(back_btn)
        
        self.add_widget(layout)
    
    def set_phone_number(self, phone):
        self.phone_number = phone
        self.phone_label.text = f'Phone: {phone}'
    
    def on_enter(self):
        self.update_history()
    
    def update_history(self):
        self.history_layout.clear_widgets()
        
        if not self.phone_number:
            self.history_layout.add_widget(Label(
                text='No phone number provided',
                size_hint_y=None,
                height=40
            ))
            return
        
        orders = self.controller.get_customer_orders(self.phone_number)
        
        if not orders:
            self.history_layout.add_widget(Label(
                text='No order history found',
                size_hint_y=None,
                height=40
            ))
            return
        
        for order in orders:
            order_id = order['order_id']
            created_at = order['created_at']
            total = order['total_amount']
            items = order['items']
            
            # Convert timestamp string to datetime if needed
            if isinstance(created_at, str):
                try:
                    created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    try:
                        created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        created_at = datetime.now()  # Fallback
            
            # Format date
            date_str = created_at.strftime('%Y-%m-%d %H:%M') if isinstance(created_at, datetime) else str(created_at)
            
            # Create order card
            card = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=150 + (len(items) * 20),
                padding=10,
                spacing=5
            )
            
            # Add a background color
            with card.canvas.before:
                Color(0.95, 0.95, 0.95, 1)
                self.rect = Rectangle(pos=card.pos, size=card.size)
            card.bind(pos=self.update_rect, size=self.update_rect)
            
            # Order header
            card.add_widget(Label(
                text=f"Order ID: {order_id}",
                size_hint_y=None,
                height=30,
                font_size='16sp',
                bold=True,
                halign='left',
                text_size=(400, None)
            ))
            
            card.add_widget(Label(
                text=f"Date: {date_str}",
                size_hint_y=None,
                height=20,
                halign='left',
                text_size=(400, None)
            ))
            
            # Items
            items_label = Label(
                text="Items:",
                size_hint_y=None,
                height=20,
                halign='left',
                text_size=(400, None),
                bold=True
            )
            card.add_widget(items_label)
            
            for item in items:
                # Each item is a tuple (name, quantity, service_type, rate, subtotal)
                name, quantity, service_type, rate, subtotal = item
                item_text = f"• {name} - {service_type} (x{quantity}) = TK {subtotal:.2f}"
                
                item_label = Label(
                    text=item_text,
                    size_hint_y=None,
                    height=20,
                    halign='left',
                    text_size=(380, None)
                )
                card.add_widget(item_label)
            
            # Total
            card.add_widget(Label(
                text=f"Total: TK {total:.2f}",
                size_hint_y=None,
                height=30,
                font_size='16sp',
                bold=True,
                halign='right',
                text_size=(400, None)
            ))
            
            self.history_layout.add_widget(card)
            
            # Add a separator
            separator = BoxLayout(size_hint_y=None, height=1)
            with separator.canvas:
                Color(0.8, 0.8, 0.8, 1)
                Rectangle(pos=separator.pos, size=(400, 1))
            self.history_layout.add_widget(separator)
    
    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size


class LaundryApp(MDApp):
    """Main application class"""
    def __init__(self, **kwargs):
        super(LaundryApp, self).__init__(**kwargs)
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Amber"
        self.theme_cls.theme_style = "Light"
        
        # Import here to avoid circular imports
        from controller.laundry_controller import LaundryController
        self.controller = LaundryController()
        
    def build(self):
        # Create screen manager
        sm = ScreenManager()
        
        # Create screens
        phone_screen = PhoneScreen(self.controller, name='phone')
        items_screen = ItemsScreen(self.controller, name='items')
        receipt_screen = ReceiptScreen(self.controller, name='receipt')
        history_screen = HistoryScreen(self.controller, name='history')
        
        # Add screens to manager
        sm.add_widget(phone_screen)
        sm.add_widget(items_screen)
        sm.add_widget(receipt_screen)
        sm.add_widget(history_screen)
        
        # Set controller's view
        self.controller.set_view(sm)
        
        return sm
    
    def on_stop(self):
        """Called when the application is closed"""
        # Clean up resources
        if self.controller:
            self.controller.cleanup()
