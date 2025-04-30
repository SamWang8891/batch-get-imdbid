import pick

options = ["[EXIT]", "[RETURN]", "Option 1", "Option 2", "Option 3"]
search_title = "Search for an option: "
option, index = pick.pick(options, search_title, indicator='=>', default_index=0)

print(option)
