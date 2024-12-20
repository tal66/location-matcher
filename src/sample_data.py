
_london_points = [
    ['battersea_park', -0.1573, 51.4797],
    ['big_ben', -0.1246, 51.5007],
    ['british_museum', -0.1270, 51.5194],
    ['buckingham_palace', -0.1419, 51.5014],
    ['camden_market', -0.1406, 51.5413],
    ['canary_wharf', -0.0235, 51.5055],
    ['covent_garden', -0.1246, 51.5115],
    ['greenwich_park', 0.0015, 51.4769],
    ['hyde_park', -0.1657, 51.5074],
    ['kensington_palace', -0.1877, 51.5058],
    ['kew_gardens', -0.2845, 51.4788],
    ['kings_cross_station', -0.1233, 51.5308],
    ['leicester_square', -0.1280, 51.5116],
    ['london_eye', -0.1195, 51.5033],
    ['london_zoo', -0.1537, 51.5353],
    ['natural_history_museum', -0.1764, 51.4967],
    ['oxford_street', -0.1426, 51.5154],
    ['piccadilly_circus', -0.1337, 51.5101],
    ['regents_park', -0.1546, 51.5313],
    ['science_museum', -0.1744, 51.4978],
    ['shard', -0.0877, 51.5045],
    ['soho_square', -0.1315, 51.5143],
    ['st_pauls_cathedral', -0.0977, 51.5138],
    ['tower_bridge', -0.0754, 51.5055],
    ['trafalgar_square', -0.1280, 51.5080],
    ['vauxhall_bridge', -0.1248, 51.4865],
    ['victoria_station', -0.1439, 51.4952],
    ['wembley_stadium', -0.2795, 51.556],
    ['westminster_abbey', -0.1284, 51.4993],
    ['abbey_road', -0.1830, 51.5326],
    ['serpentine_gallery', -0.1731, 51.5043],
    ['royal_observatory', 0.0000, 51.4769],
    ['temple_church', -0.1081, 51.5139],
    ['smithfield_market', -0.1009, 51.5174],
    ['whitechapel_gallery', -0.0719, 51.5165],
    ['chiswick_house', -0.2582, 51.4847],
    ['hms_belfast', -0.0803, 51.5065],
    ['royal_albert_hall', -0.1774, 51.5009],
    ['portobello_road_market', -0.2064, 51.5205],
    ['barking', 0.0815, 51.5284],
    ['brent_cross', -0.2299, 51.5781],
    ['croydon', -0.1007, 51.3720],
    ['ealing', -0.3022, 51.5066],
    ['enfield', -0.0815, 51.6511],
    ['greenwich', -0.0055, 51.4822],
    ['hammersmith', -0.2259, 51.4900],
    ['harrow', -0.3352, 51.5936],
    ['ilford', 0.0710, 51.5580],
    ['kingston', -0.3000, 51.4113],
    ['northolt', -0.3701, 51.5457],
    ['romford', 0.1760, 51.5753],
    ['southwark', -0.0940, 51.5052],
    ['walthamstow', -0.0182, 51.5780],
    ['wembley', -0.2765, 51.5580],
    ['windsor', -0.6101, 51.4830],

    ['alexandra_palace', -0.1206, 51.5944],
    ['brixton', -0.1142, 51.4612],
    ['canada_water', -0.0496, 51.4987],
    ['chislehurst', 0.0705, 51.4170],
    ['clapham_common', -0.1472, 51.4616],
    ['crystal_palace', -0.0711, 51.4183],
    ['dulwich_village', -0.0861, 51.4467],
    ['finchley_central', -0.1913, 51.6011],
    ['hackney_central', -0.0551, 51.5465],
    ['hampstead_heath', -0.1657, 51.5569],
    ['isle_of_dogs', -0.0175, 51.4948],
    ['mill_hill', -0.2396, 51.6158],
    ['muswell_hill', -0.1422, 51.5923],
    ['pinner', -0.3823, 51.5936],
    ['richmond_park', -0.2760, 51.4358],
    ['stratford', -0.0036, 51.5417],
    ['twickenham', -0.3329, 51.4444],
    ['wandsworth_common', -0.1764, 51.4522],
    ['wimbledon_common', -0.2356, 51.4341],
    ['woolwich', 0.0695, 51.4918],

]

DB_LONDON_VALUES = ",\n".join([
    f"('{name}', ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326), NOW())"
    for name, lon, lat in _london_points
])

DB_NOISED_VALUES = """
"""