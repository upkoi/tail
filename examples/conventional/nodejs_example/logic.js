let args = process.argv.slice(2)
let parsedArgs = JSON.parse(args.join(""))

// Your JS logic here
// Example (but not fully accurate) idea of parsedArgs is 
// [1, 2, 0, 1, 0, 0, 1, 1, 2, 0, 1, 0, 0, 1, 1, 2, 0, 1, 0, 0, 1, 1, 2, 0, 1, 0, 0, 1, 1, 2, 0, 1, 0, 0, 1, 1, 2, 0, 1, 0, 0, 1, 1, 2, 0, 1, 0, 0, 1 ]

console.log(parsedArgs)

