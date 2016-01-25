<?php
/*
Plugin Name: FabLabLux Machine Schedule
Description: Display the machine schedule on a page during open access hours.
Author: Alexandre Saint
Version: 1.0
*/

defined('ABSPATH') or exit; 

include_once(plugin_dir_path(__FILE__) . 'open-access.php');
include_once(plugin_dir_path(__FILE__) . 'options.php');
include_once(plugin_dir_path(__FILE__) . 'rest-api.php');
include_once(plugin_dir_path(__FILE__) . 'schedule-view.php');
include_once(plugin_dir_path(__FILE__) . 'table.php');

/**
 * Display the machine use schedule during open access time.
 */
class MachineSchedule {

    static $instance = null;

    private $options = null;

    private function __construct() {
        $this->api = new MachineScheduleApi();
        $this->api->activate();

        $this->options = MachineScheduleOptions::instance();

        register_activation_hook(
            __FILE__,
            array('MachineSchedule', 'activate')
        );
        register_uninstall_hook(
            __FILE__,
            array('MachineSchedule', 'uninstall')
        );
        add_action('admin_menu', array($this, 'action_admin_menu'));
        add_filter('the_content', array($this, 'the_content'), 20, 1);
    } 

    public static function instance() {
        if (is_null(self::$instance)) {
            self::$instance = new self;
        }
        return self::$instance;
    }

    /**
     * Set up the plugin on activation.
     */
    public static function activate() {
        if (!current_user_can('activate_plugins')) {
            return;
        }
        // By getting the instance, the options are initialized in the
        // database.
        $options = MachineScheduleOptions::instance();
    }

    /**
     * Clear plugin data on uninstallation.
     */
    public static function uninstall() {
        if (!current_user_can('activate_plugins')) {
            return;
        }
        $options = MachineScheduleOptions::intance();
        $options->delete();
    }

    /**
     * Add an options page in the admin menu.
     */
    public function action_admin_menu() {
        $this->options->register_menu();
    }

    /**
     * Display the machine schedule table at the end of the content.
     *
     * @param string $content The original content.
     * @return string The modified content.
     */
    public function the_content($content) {
        if (!OpenAccess::status()) {
            return $content;
        }

        $page_id = $this->options['page_id'];
        if (!is_page($page_id)) {
            return $content;
        }

        $table_html = ScheduleView::render($page_id);
        $content = $table_html . $content;

        return $content;
    }
}

$machine_schedule = MachineSchedule::instance();

?>
