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

    /**
     * Name of the shortcode tag to display the schedule.
     */
    private $shortcode = "schedule";

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
        add_shortcode($this->shortcode, array($this, 'shortcode_handler'));
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
     * Register our options view in the admin menu.
     */
    public function action_admin_menu() {
        $this->options->register_menu();
    }

    /**
     * Display the machine schedule on the main content area.
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

        $page_id = $this->options['page_id'];
        $table = Table::get_visible($page_id);
        $machines = Table::get_visible_machines();
        $slots = Table::get_visible_slots();
        $table_html = ScheduleView::render($table, $machines, $slots);
        $content = $table_html . $content;

        return $content;
    }

    /**
     * Render the machine schedule.
     *
     * @param string $content The original content.
     * @return string The modified content.
     */
    public function shortcode_handler($attributes, $content=null) {
        if (!OpenAccess::status()) {
            return "";
        }

        $page_id = $this->options['page_id'];
        $table = Table::get_visible($page_id);
        $machines = Table::get_visible_machines();
        $slots = Table::get_visible_slots();
        $table_html = ScheduleView::render($table, $machines, $slots);

        return $table_html;
    }
}

$machine_schedule = MachineSchedule::instance();

?>
