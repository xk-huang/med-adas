output_dir="outputs"

# Loop through all PNG files in the directory
for file in "$output_dir"/*.png; do
    # Extract the filename without the path
    filename=$(basename "$file")
    
    # Split the filename by '_' and extract dataset and model
    dataset_name=$(echo "$filename" | cut -d'_' -f1)
    model_name=$(echo "$filename" | cut -d'_' -f2)
    
    # Create the target directory
    target_dir="$output_dir/$model_name/$dataset_name"
    mkdir -p "$target_dir"
    
    # Copy the file to the target directory
    cp "$file" "$target_dir/"
done