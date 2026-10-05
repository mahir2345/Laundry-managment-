from kivy.lang import Builder
from controller.laundry_controller import LaundryController
from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager
from view.laundry_view import PhoneScreen, ItemsScreen, ReceiptScreen, HistoryScreen

class LaundryApp(MDApp):
    def __init__(self, **kwargs):
        super(LaundryApp, self).__init__(**kwargs)
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Amber"
        self.theme_cls.theme_style = "Light"
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
        self.controller.cleanup()

if __name__ == "__main__":
    # Load the KV file
    Builder.load_file('view/laundry.kv')
    LaundryApp().run()
