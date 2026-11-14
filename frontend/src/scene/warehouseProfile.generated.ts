export const staticWarehouse = {
  "layout": {
    "aisles": [
      {
        "axis": "x",
        "bounds": {
          "x_max": 4.5,
          "x_min": -13.25,
          "y_max": 6.5,
          "y_min": 4.25
        },
        "id": "aisle_a",
        "label": "ANA KORİDOR A",
        "role": "main"
      },
      {
        "axis": "x",
        "bounds": {
          "x_max": 12.25,
          "x_min": -13.25,
          "y_max": 3.25,
          "y_min": 1.0
        },
        "id": "aisle_b",
        "label": "ANA KORİDOR B",
        "role": "main"
      },
      {
        "axis": "x",
        "bounds": {
          "x_max": 12.25,
          "x_min": -13.25,
          "y_max": 0.0,
          "y_min": -2.25
        },
        "id": "aisle_c",
        "label": "ANA KORİDOR C",
        "role": "main"
      },
      {
        "axis": "x",
        "bounds": {
          "x_max": 12.25,
          "x_min": -13.25,
          "y_max": -3.25,
          "y_min": -5.5
        },
        "id": "aisle_d",
        "label": "ANA KORİDOR D",
        "role": "main"
      },
      {
        "axis": "y",
        "bounds": {
          "x_max": -11.5,
          "x_min": -13.25,
          "y_max": 8.0,
          "y_min": -7.25
        },
        "id": "cross_w",
        "label": "ENİNE GEÇİT W",
        "role": "cross"
      },
      {
        "axis": "y",
        "bounds": {
          "x_max": 0.0,
          "x_min": -2.0,
          "y_max": 8.0,
          "y_min": -7.25
        },
        "id": "cross_m",
        "label": "ENİNE GEÇİT M",
        "role": "cross"
      },
      {
        "axis": "y",
        "bounds": {
          "x_max": 12.25,
          "x_min": 10.5,
          "y_max": 4.75,
          "y_min": -7.25
        },
        "id": "cross_e",
        "label": "ENİNE GEÇİT E",
        "role": "cross"
      },
      {
        "axis": "x",
        "bounds": {
          "x_max": -11.5,
          "x_min": -15.0,
          "y_max": 0.75,
          "y_min": -0.75
        },
        "id": "inbound_access",
        "label": "MAL KABUL GİRİŞİ",
        "role": "access"
      }
    ],
    "approach_clearance_m": 0.45,
    "bounds": {
      "x_max": 15.0,
      "x_min": -15.0,
      "y_max": 9.0,
      "y_min": -9.0
    },
    "dock_approach_m": 2.0,
    "dock_rack_clearance_m": 2.0,
    "door": {
      "center": 0.0,
      "side": "west",
      "width": 2.0
    },
    "example_tasks": [
      {
        "dropoff": "packing_1",
        "id": "rack_to_packing",
        "pickup": "pick_A1",
        "priority": "LOW"
      },
      {
        "dropoff": "delivery-01",
        "id": "rack_to_shipping",
        "pickup": "pick_C2",
        "priority": "MEDIUM"
      },
      {
        "dropoff": "pick_B1",
        "id": "inbound_to_rack",
        "pickup": "inbound_1",
        "priority": "LOW"
      }
    ],
    "frame_id": "map",
    "grid_m": 0.25,
    "racks": [
      {
        "bays": 6,
        "bounds": {
          "x_max": -2.25,
          "x_min": -11.5,
          "y_max": 7.5,
          "y_min": 6.5
        },
        "height": 1.15,
        "id": "rack_A1"
      },
      {
        "bays": 4,
        "bounds": {
          "x_max": 4.25,
          "x_min": 0.25,
          "y_max": 7.5,
          "y_min": 6.5
        },
        "height": 1.15,
        "id": "rack_A2"
      },
      {
        "bays": 6,
        "bounds": {
          "x_max": -2.25,
          "x_min": -11.5,
          "y_max": 4.25,
          "y_min": 3.25
        },
        "height": 1.15,
        "id": "rack_B1"
      },
      {
        "bays": 6,
        "bounds": {
          "x_max": 10.25,
          "x_min": 0.25,
          "y_max": 4.25,
          "y_min": 3.25
        },
        "height": 1.15,
        "id": "rack_B2"
      },
      {
        "bays": 6,
        "bounds": {
          "x_max": -2.25,
          "x_min": -11.5,
          "y_max": 1.0,
          "y_min": 0.0
        },
        "height": 1.15,
        "id": "rack_C1"
      },
      {
        "bays": 6,
        "bounds": {
          "x_max": 10.25,
          "x_min": 3.0,
          "y_max": 1.0,
          "y_min": 0.0
        },
        "height": 1.15,
        "id": "rack_C2"
      },
      {
        "bays": 6,
        "bounds": {
          "x_max": -2.25,
          "x_min": -11.5,
          "y_max": -2.25,
          "y_min": -3.25
        },
        "height": 1.15,
        "id": "rack_D1"
      },
      {
        "bays": 6,
        "bounds": {
          "x_max": 10.25,
          "x_min": 0.25,
          "y_max": -2.25,
          "y_min": -3.25
        },
        "height": 1.15,
        "id": "rack_D2"
      },
      {
        "bays": 6,
        "bounds": {
          "x_max": -2.25,
          "x_min": -11.5,
          "y_max": -5.5,
          "y_min": -6.5
        },
        "height": 1.15,
        "id": "rack_E1"
      },
      {
        "bays": 6,
        "bounds": {
          "x_max": 10.25,
          "x_min": 0.25,
          "y_max": -5.5,
          "y_min": -6.5
        },
        "height": 1.15,
        "id": "rack_E2"
      }
    ],
    "transfer_points": [
      {
        "id": "pick_A1",
        "kind": "pickup",
        "pose": {
          "x": -7.0,
          "y": 5.75,
          "yaw": 1.5707963267948966
        },
        "rack_id": "rack_A1",
        "roles": [
          "pickup",
          "dropoff"
        ],
        "zone_id": "pick_zone_A1"
      },
      {
        "id": "pick_A2",
        "kind": "pickup",
        "pose": {
          "x": 2.25,
          "y": 5.75,
          "yaw": 1.5707963267948966
        },
        "rack_id": "rack_A2",
        "roles": [
          "pickup",
          "dropoff"
        ],
        "zone_id": "pick_zone_A2"
      },
      {
        "id": "pick_B1",
        "kind": "pickup",
        "pose": {
          "x": -7.0,
          "y": 2.5,
          "yaw": 1.5707963267948966
        },
        "rack_id": "rack_B1",
        "roles": [
          "pickup",
          "dropoff"
        ],
        "zone_id": "pick_zone_B1"
      },
      {
        "id": "pick_B2",
        "kind": "pickup",
        "pose": {
          "x": 6.0,
          "y": 2.5,
          "yaw": 1.5707963267948966
        },
        "rack_id": "rack_B2",
        "roles": [
          "pickup",
          "dropoff"
        ],
        "zone_id": "pick_zone_B2"
      },
      {
        "id": "pick_C1",
        "kind": "pickup",
        "pose": {
          "x": -7.0,
          "y": -0.75,
          "yaw": 1.5707963267948966
        },
        "rack_id": "rack_C1",
        "roles": [
          "pickup",
          "dropoff"
        ],
        "zone_id": "pick_zone_C1"
      },
      {
        "id": "pick_C2",
        "kind": "pickup",
        "pose": {
          "x": 6.0,
          "y": -0.75,
          "yaw": 1.5707963267948966
        },
        "rack_id": "rack_C2",
        "roles": [
          "pickup",
          "dropoff"
        ],
        "zone_id": "pick_zone_C2"
      },
      {
        "id": "pick_D1",
        "kind": "pickup",
        "pose": {
          "x": -8.0,
          "y": -4.0,
          "yaw": 1.5707963267948966
        },
        "rack_id": "rack_D1",
        "roles": [
          "pickup",
          "dropoff"
        ],
        "zone_id": "pick_zone_D1"
      },
      {
        "id": "pick_D2",
        "kind": "pickup",
        "pose": {
          "x": 7.0,
          "y": -4.0,
          "yaw": 1.5707963267948966
        },
        "rack_id": "rack_D2",
        "roles": [
          "pickup",
          "dropoff"
        ],
        "zone_id": "pick_zone_D2"
      },
      {
        "id": "pick_E1",
        "kind": "pickup",
        "pose": {
          "x": -5.0,
          "y": -4.75,
          "yaw": -1.5707963267948966
        },
        "rack_id": "rack_E1",
        "roles": [
          "pickup",
          "dropoff"
        ],
        "zone_id": "pick_zone_E1"
      },
      {
        "id": "pick_E2",
        "kind": "pickup",
        "pose": {
          "x": 3.0,
          "y": -4.75,
          "yaw": -1.5707963267948966
        },
        "rack_id": "rack_E2",
        "roles": [
          "pickup",
          "dropoff"
        ],
        "zone_id": "pick_zone_E2"
      },
      {
        "id": "inbound_1",
        "kind": "pickup",
        "pose": {
          "x": -13.75,
          "y": -1.25,
          "yaw": 3.141592653589793
        },
        "rack_id": null,
        "roles": null,
        "zone_id": "inbound_zone"
      },
      {
        "id": "inbound_2",
        "kind": "pickup",
        "pose": {
          "x": -13.75,
          "y": 1.25,
          "yaw": 3.141592653589793
        },
        "rack_id": null,
        "roles": null,
        "zone_id": "inbound_zone"
      },
      {
        "id": "packing_1",
        "kind": "dropoff",
        "pose": {
          "x": -2.75,
          "y": -7.75,
          "yaw": -1.5707963267948966
        },
        "rack_id": null,
        "roles": null,
        "zone_id": "packing_zone"
      },
      {
        "id": "packing_2",
        "kind": "dropoff",
        "pose": {
          "x": 0.75,
          "y": -7.75,
          "yaw": -1.5707963267948966
        },
        "rack_id": null,
        "roles": null,
        "zone_id": "packing_zone"
      },
      {
        "id": "delivery-01",
        "kind": "dropoff",
        "pose": {
          "x": 13.75,
          "y": -6.75,
          "yaw": 0.0
        },
        "rack_id": null,
        "roles": null,
        "zone_id": "shipping_zone"
      },
      {
        "id": "shipping_2",
        "kind": "dropoff",
        "pose": {
          "x": 13.75,
          "y": -5.25,
          "yaw": 0.0
        },
        "rack_id": null,
        "roles": null,
        "zone_id": "shipping_zone"
      },
      {
        "id": "shipping_3",
        "kind": "dropoff",
        "pose": {
          "x": 13.75,
          "y": -3.75,
          "yaw": 0.0
        },
        "rack_id": null,
        "roles": null,
        "zone_id": "shipping_zone"
      },
      {
        "id": "quality_1",
        "kind": "dropoff",
        "pose": {
          "x": 1.5,
          "y": 0.5,
          "yaw": 1.5707963267948966
        },
        "rack_id": null,
        "roles": null,
        "zone_id": "quality_zone"
      }
    ],
    "wall_height_m": 1.9,
    "wall_thickness_m": 0.1,
    "walls": [
      {
        "bounds": {
          "x_max": 15.0,
          "x_min": -15.0,
          "y_max": 9.05,
          "y_min": 8.95
        },
        "edge": 9.0,
        "id": "wall_north_1",
        "side": "north"
      },
      {
        "bounds": {
          "x_max": 15.0,
          "x_min": -15.0,
          "y_max": -8.95,
          "y_min": -9.05
        },
        "edge": -9.0,
        "id": "wall_south_1",
        "side": "south"
      },
      {
        "bounds": {
          "x_max": -14.95,
          "x_min": -15.05,
          "y_max": -1.0,
          "y_min": -9.0
        },
        "edge": -15.0,
        "id": "wall_west_1",
        "side": "west"
      },
      {
        "bounds": {
          "x_max": -14.95,
          "x_min": -15.05,
          "y_max": 9.0,
          "y_min": 1.0
        },
        "edge": -15.0,
        "id": "wall_west_2",
        "side": "west"
      },
      {
        "bounds": {
          "x_max": 15.05,
          "x_min": 14.95,
          "y_max": 9.0,
          "y_min": -9.0
        },
        "edge": 15.0,
        "id": "wall_east_1",
        "side": "east"
      }
    ],
    "zones": [
      {
        "bounds": {
          "x_max": -6.25,
          "x_min": -7.75,
          "y_max": 6.25,
          "y_min": 5.25
        },
        "callout": null,
        "id": "pick_zone_A1",
        "kind": "pickup",
        "label": "Raf A"
      },
      {
        "bounds": {
          "x_max": 3.0,
          "x_min": 1.5,
          "y_max": 6.25,
          "y_min": 5.25
        },
        "callout": null,
        "id": "pick_zone_A2",
        "kind": "pickup",
        "label": "Raf A"
      },
      {
        "bounds": {
          "x_max": -6.25,
          "x_min": -7.75,
          "y_max": 3.0,
          "y_min": 2.0
        },
        "callout": null,
        "id": "pick_zone_B1",
        "kind": "pickup",
        "label": "Raf B"
      },
      {
        "bounds": {
          "x_max": 6.75,
          "x_min": 5.25,
          "y_max": 3.0,
          "y_min": 2.0
        },
        "callout": null,
        "id": "pick_zone_B2",
        "kind": "pickup",
        "label": "Raf B"
      },
      {
        "bounds": {
          "x_max": -6.25,
          "x_min": -7.75,
          "y_max": -0.25,
          "y_min": -1.25
        },
        "callout": null,
        "id": "pick_zone_C1",
        "kind": "pickup",
        "label": "Raf C"
      },
      {
        "bounds": {
          "x_max": 6.75,
          "x_min": 5.25,
          "y_max": -0.25,
          "y_min": -1.25
        },
        "callout": null,
        "id": "pick_zone_C2",
        "kind": "pickup",
        "label": "Raf C"
      },
      {
        "bounds": {
          "x_max": -7.25,
          "x_min": -8.75,
          "y_max": -3.5,
          "y_min": -4.5
        },
        "callout": null,
        "id": "pick_zone_D1",
        "kind": "pickup",
        "label": "Raf D"
      },
      {
        "bounds": {
          "x_max": 7.75,
          "x_min": 6.25,
          "y_max": -3.5,
          "y_min": -4.5
        },
        "callout": null,
        "id": "pick_zone_D2",
        "kind": "pickup",
        "label": "Raf D"
      },
      {
        "bounds": {
          "x_max": -4.25,
          "x_min": -5.75,
          "y_max": -4.25,
          "y_min": -5.25
        },
        "callout": null,
        "id": "pick_zone_E1",
        "kind": "pickup",
        "label": "Raf E"
      },
      {
        "bounds": {
          "x_max": 3.75,
          "x_min": 2.25,
          "y_max": -4.25,
          "y_min": -5.25
        },
        "callout": null,
        "id": "pick_zone_E2",
        "kind": "pickup",
        "label": "Raf E"
      },
      {
        "bounds": {
          "x_max": -13.0,
          "x_min": -14.5,
          "y_max": 2.75,
          "y_min": -2.75
        },
        "callout": null,
        "id": "inbound_zone",
        "kind": "pickup",
        "label": "Mal kabul"
      },
      {
        "bounds": {
          "x_max": 2.0,
          "x_min": -4.0,
          "y_max": -7.0,
          "y_min": -8.5
        },
        "callout": null,
        "id": "packing_zone",
        "kind": "dropoff",
        "label": "Paketleme"
      },
      {
        "bounds": {
          "x_max": 14.75,
          "x_min": 12.5,
          "y_max": -3.25,
          "y_min": -7.75
        },
        "callout": null,
        "id": "shipping_zone",
        "kind": "dropoff",
        "label": "Sevkiyat"
      },
      {
        "bounds": {
          "x_max": 2.75,
          "x_min": 0.25,
          "y_max": 1.5,
          "y_min": -0.25
        },
        "callout": null,
        "id": "quality_zone",
        "kind": "dropoff",
        "label": "Kalite kontrol"
      },
      {
        "bounds": {
          "x_max": 14.75,
          "x_min": 6.25,
          "y_max": 8.75,
          "y_min": 5.0
        },
        "callout": null,
        "id": "charge_zone",
        "kind": "charging",
        "label": "Şarj"
      },
      {
        "bounds": {
          "x_max": 6.0,
          "x_min": 4.5,
          "y_max": 8.5,
          "y_min": 4.75
        },
        "callout": null,
        "id": "park_zone",
        "kind": "parking",
        "label": "Park"
      }
    ]
  },
  "profile_digest": "8e8396b60c306e795ea84275ac56aa41a47fc8cf090fe14ad9627988bc91fda2",
  "profile_id": "warehouse_distributed_30x18"
} as const
