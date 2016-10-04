<?php

include_once(plugin_dir_path(__FILE__) . 'options.php');

/**
 * Check the open access status of the fablab.
 */
class OpenAccess {

    /**
     * Return true if the fablab is currently in open access.
     *
     * @return bool
     */
    public static function status() {
        $options = MachineScheduleOptions::instance();

        $now = OpenAccess::get_local_date($options['timezone']);

        $time_slots = $options['opening_hours'];
        foreach($time_slots as $time_slot) {
            if (OpenAccess::date_in_time_slot($now, $time_slot)) {
                return true;
            }
        }

        return false;
    }

    private static function get_local_date($time_zone_name) {
        $time_zone = new DateTimeZone($time_zone_name);
        $local_date = new DateTime("now", $time_zone);
        $timestamp = $local_date->getTimestamp() + $local_date->getOffset();
        $now = getdate($timestamp);
        return $now;
    }

    private static function date_in_time_slot($date, $time_slot) {
        if (count($time_slot) != 5) {
            return false;
        }

        list($day, $start_hour, $start_min, $end_hour, $end_min) = $time_slot;

        $day_match = $date['weekday'] === $day;
        $past_start_hour = $date['hours'] > $start_hour ||
                           ($date['hours'] == $start_hour &&
                            $date['minutes'] >= $start_min);
        $before_end_hour = $date['hours'] < $end_hour ||
                           ($date['hours'] == $end_hour &&
                            $date['minutes'] < $end_min);

        return $day_match && $past_start_hour && $before_end_hour;
    }
}

?>
